// Tier 1 for the fresh authorization check (onCrack unit R4.3). See FreshMicro.fsproj.
//
//   dotnet run -c Release --project bench/fresh-micro -- [--seed crowd] [--room hq] [--route room|messages|sidebar] [--conc 16]
//       [--post-rate 0] [--secs 3] [--rounds 5] [--warmup 10] [--variants "hold;nohold"]
//
// A variant is `hold` (`FreshHold.Enabled` true: the checks keep a read transaction while the WAL index proves nothing
// committed) or `nohold` (R3.2: one read transaction per check). Every window sets one variant, reads the route for --secs
// from --conc keep-alive connections signed in as one member, and reports answers per second, process CPU and bytes
// allocated per answer; the rounds alternate the variants (A B A B ...) so drift cancels. The clients are in the same
// process, so CPU per answer includes theirs (a fixed few microseconds): compare variants, never report these as results.
module FreshMicro

open System
open System.Collections.Generic
open System.Diagnostics
open System.IO
open System.Net
open System.Net.Http
open System.Net.Sockets
open System.Text
open System.Text.Json
open System.Text.RegularExpressions
open System.Threading
open System.Threading.Tasks
open Campfire.App

let root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../.."))

let arg (argv: string[]) (name: string) (fallback: string) =
    match Array.tryFindIndex ((=) name) argv with
    | Some i when i + 1 < argv.Length -> argv[i + 1]
    | _ -> fallback

let rec copyDir (from: string) (target: string) =
    Directory.CreateDirectory target |> ignore
    for file in Directory.GetFiles from do
        File.Copy(file, Path.Combine(target, Path.GetFileName file))
    for sub in Directory.GetDirectories from do
        copyDir sub (Path.Combine(target, Path.GetFileName sub))

let freePort () =
    let l = new TcpListener(IPAddress.Loopback, 0)
    l.Start()
    let p = (l.LocalEndpoint :?> IPEndPoint).Port
    l.Stop()
    p

/// One signed-in poster: its cookie header and CSRF token.
type Poster = { Cookie: string; Csrf: string }

let csrfOf (html: string) =
    let m = Regex.Match(html, "<meta name=\"csrf-token\" content=\"([^\"]*)\"")
    if m.Success then m.Groups[1].Value else ""

let signIn (port: int) (email: string) (password: string) (room: int64) (n: int) : Task<Poster> =
    task {
        let cookies = CookieContainer()
        use handler = new HttpClientHandler(CookieContainer = cookies, AllowAutoRedirect = false)
        use client = new HttpClient(handler, BaseAddress = Uri($"http://127.0.0.1:{port}"))
        client.DefaultRequestHeaders.Add("X-Forwarded-For", $"10.88.0.{n + 1}")
        let! page = client.GetStringAsync("/session/new")
        let form =
            new FormUrlEncodedContent(
                dict [ "email_address", email; "password", password; "authenticity_token", csrfOf page ]
            )
        let! r = client.PostAsync("/session", form)
        if int r.StatusCode <> 302 && int r.StatusCode <> 303 then failwithf "sign-in of %s answered %d" email (int r.StatusCode)
        let! roomPage = client.GetStringAsync($"/rooms/{room}")
        let header = cookies.GetCookieHeader(Uri($"http://127.0.0.1:{port}"))
        return { Cookie = header; Csrf = csrfOf roomPage }
    }

let getRequest (path: string) (p: Poster) : byte[] =
    let head =
        $"GET {path} HTTP/1.1\r\nhost: 127.0.0.1\r\naccept: text/html,application/xhtml+xml\r\naccept-encoding: gzip\r\nuser-agent: fresh-micro\r\ncookie: {p.Cookie}\r\n\r\n"
    Encoding.ASCII.GetBytes head

let mutable private nonce = 0L

let postRequest (room: int64) (p: Poster) : byte[] =
    let id = Interlocked.Increment(&nonce)
    let body =
        "message%5Bbody%5D=bench+write+" + string id + "&message%5Bclient_message_id%5D=fm-" + Guid.NewGuid().ToString("N")
        + "&authenticity_token=" + Uri.EscapeDataString p.Csrf
    let head =
        $"POST /rooms/{room}/messages HTTP/1.1\r\nhost: 127.0.0.1\r\naccept: text/vnd.turbo-stream.html, text/html, application/xhtml+xml\r\naccept-encoding: gzip\r\ncookie: {p.Cookie}\r\nx-csrf-token: {p.Csrf}\r\ncontent-type: application/x-www-form-urlencoded\r\ncontent-length: {body.Length}\r\n\r\n"
    Encoding.ASCII.GetBytes(head + body)

/// Posts answered (2xx), and anything else.
type Counts() =
    [<DefaultValue>]
    val mutable Ok: int64

    [<DefaultValue>]
    val mutable Bad: int64

    /// Answers slower than 100 ms, and the slowest (microseconds).
    [<DefaultValue>]
    val mutable Slow: int64

    [<DefaultValue>]
    val mutable MaxUs: int64

/// One keep-alive connection posting until `stop`; reads each response to its end (Content-Length or chunked).
let poster (port: int) (mk: unit -> byte[]) (pauseMs: int) (counts: Counts) (stop: CancellationToken) : Task =
    task {
        use client = new TcpClient(NoDelay = true)
        do! client.ConnectAsync(IPAddress.Loopback, port)
        let s = client.GetStream()
        let buf = Array.zeroCreate<byte> 65536
        let mutable have = 0
        while not stop.IsCancellationRequested do
            let t0 = Stopwatch.GetTimestamp()
            if pauseMs > 0 then do! Task.Delay pauseMs
            do! s.WriteAsync(mk ())
            // headers
            let mutable headEnd = -1
            while headEnd < 0 do
                let! n = s.ReadAsync(buf, have, buf.Length - have)
                if n = 0 then failwith "connection closed"
                have <- have + n
                let span = ReadOnlySpan<byte>(buf, 0, have)
                headEnd <- span.IndexOf("\r\n\r\n"B)
            let head = Encoding.ASCII.GetString(buf, 0, headEnd)
            let status = int (head.Substring(9, 3))
            let m = Regex.Match(head, "(?i)content-length: *(\\d+)")
            let mutable total = 0
            if m.Success then
                total <- headEnd + 4 + int m.Groups[1].Value
                while have < total do
                    let! n = s.ReadAsync(buf, have, buf.Length - have)
                    if n = 0 then failwith "connection closed"
                    have <- have + n
            else
                // Chunked (a page in parts that is not frozen yet): to the last chunk.
                if not (Regex.IsMatch(head, "(?i)transfer-encoding: *chunked")) then failwithf "no content-length: %s" head
                let mutable fin = -1
                while fin < 0 do
                    let span = ReadOnlySpan<byte>(buf, headEnd + 4, have - headEnd - 4)
                    let i = span.IndexOf("\r\n0\r\n\r\n"B)
                    if i >= 0 then fin <- headEnd + 4 + i + 7
                    elif have - headEnd - 4 = 5 && span.SequenceEqual("0\r\n\r\n"B) then fin <- have
                    else
                        let! n = s.ReadAsync(buf, have, buf.Length - have)
                        if n = 0 then failwith "connection closed"
                        have <- have + n
                total <- fin
            Buffer.BlockCopy(buf, total, buf, 0, have - total)
            have <- have - total
            let us = (Stopwatch.GetTimestamp() - t0) * 1_000_000L / Stopwatch.Frequency
            if us > 100_000L then Interlocked.Increment(&counts.Slow) |> ignore
            let mutable seen = Volatile.Read(&counts.MaxUs)
            while us > seen && Interlocked.CompareExchange(&counts.MaxUs, us, seen) <> seen do
                seen <- Volatile.Read(&counts.MaxUs)
            if status >= 200 && status < 300 then Interlocked.Increment(&counts.Ok) |> ignore
            else
                if Interlocked.Increment(&counts.Bad) <= 3L then eprintfn "status %d: %s" status (head.Split('\r')[0])
    }

let cpu () = Process.GetCurrentProcess().TotalProcessorTime

[<EntryPoint>]
let main argv =
    let seedName = arg argv "--seed" "crowd"
    let roomLabel = arg argv "--room" "hq"
    let concs = (arg argv "--conc" "16").Split(',') |> Array.map int
    let secs = float (arg argv "--secs" "3")
    let rounds = int (arg argv "--rounds" "5")
    let warm = float (arg argv "--warmup" "10")
    let variants = (arg argv "--variants" "hold;nohold").Split(';') |> Array.map (fun v -> v.Trim())
    let postersN = 1
    let route = arg argv "--route" "room"
    let postRate = int (arg argv "--post-rate" "0")
    let seed = Path.Combine(root, "parity/.seed", seedName)
    let labels = JsonDocument.Parse(File.ReadAllText(Path.Combine(seed, "labels.json"))).RootElement
    let room = labels.GetProperty("rooms." + roomLabel).GetInt64()
    let dir = Directory.CreateTempSubdirectory("fresh-micro").FullName
    Directory.CreateDirectory(Path.Combine(dir, "db")) |> ignore
    for f in [ "production.sqlite3"; "production.sqlite3-wal"; "production.sqlite3-shm" ] do
        let from = Path.Combine(seed, "db", f)
        if File.Exists from then File.Copy(from, Path.Combine(dir, "db", f))
    if Directory.Exists(Path.Combine(seed, "storage")) then copyDir (Path.Combine(seed, "storage")) (Path.Combine(dir, "files"))
    let port = freePort ()
    for line in File.ReadAllLines(Path.Combine(root, "parity/.env.reference")) do
        if not (line.StartsWith "#") && line.Contains "=" then
            let i = line.IndexOf '='
            Environment.SetEnvironmentVariable(line.Substring(0, i), line.Substring(i + 1))
    // --env K=V,K2=V2: after the parity environment (an empty value unsets).
    for kv in (arg argv "--env" "").Split(',', StringSplitOptions.RemoveEmptyEntries) do
        let i = kv.IndexOf '='
        Environment.SetEnvironmentVariable(kv.Substring(0, i), (match kv.Substring(i + 1) with "" -> null | v -> v))
    Environment.SetEnvironmentVariable("CAMPFIRE_STORAGE_PATH", dir)
    Environment.SetEnvironmentVariable("HTTP_PORT", string port)
    Environment.SetEnvironmentVariable("LOG_REQUESTS", "false")
    let config =
        match Campfire.App.AppConfig.fromEnv () with
        | Ok c -> c
        | Error e -> failwith e
    let loggers = Microsoft.Extensions.Logging.Abstractions.NullLoggerFactory.Instance
    let _server = Boot.serve config loggers
    // wait for /up
    let mutable up = false
    while not up do
        try
            use c = new HttpClient()
            up <- (c.GetAsync($"http://127.0.0.1:{port}/up").Result).IsSuccessStatusCode
        with _ -> Thread.Sleep 100
    let password = labels.GetProperty("passwords.all").GetString()
    let emails = [ "emails.david"; "emails.jason"; "emails.kevin"; "emails.jz" ] |> List.map (fun k -> labels.GetProperty(k).GetString())
    let members =
        let dbPath = Path.Combine(dir, "db/production.sqlite3")
        use c = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={dbPath};Mode=ReadOnly")
        c.Open()
        use cmd = c.CreateCommand()
        cmd.CommandText <- $"SELECT u.email_address FROM memberships m JOIN users u ON u.id = m.user_id WHERE m.room_id = {room} AND u.status = 0 AND u.role <> 2 AND u.email_address IS NOT NULL ORDER BY u.id"
        use r = cmd.ExecuteReader()
        [ while r.Read() do yield r.GetString 0 ] |> Set.ofList
    let who = emails |> List.filter members.Contains |> List.truncate (max postersN 1)
    let posters = who |> List.mapi (fun i e -> (signIn port e password room i).Result) |> Array.ofList
    eprintfn "room %s (%d), %d members, posting as %s" roomLabel room members.Count (String.Join(", ", who))
    let before =
        let dbPath = Path.Combine(dir, "db/production.sqlite3")
        use c = new Microsoft.Data.Sqlite.SqliteConnection($"Data Source={dbPath};Mode=ReadOnly")
        c.Open()
        use cmd = c.CreateCommand()
        cmd.CommandText <- $"SELECT id FROM messages WHERE room_id = {room} ORDER BY id DESC LIMIT 1 OFFSET 20"
        string (cmd.ExecuteScalar())
    let path = match route with "messages" -> $"/rooms/{room}/messages?before={before}" | "sidebar" -> "/" | _ -> $"/rooms/{room}"
    let run (variant: string) (conc: int) (seconds: float) =
        Campfire.Db.FreshHold.Enabled <- (variant = "hold")
        let counts = Counts()
        use stop = new CancellationTokenSource()
        let tasks =
            [| for i in 0 .. conc - 1 ->
                   (task {
                       try
                           let who = posters[i % posters.Length]
                           do! poster port (fun () -> getRequest path who) 0 counts stop.Token
                       with e ->
                           if Interlocked.Increment(&counts.Bad) <= 3L then eprintfn "client failed: %s" (e.Message.Split('\n')[0])
                   }) :> Task |]
        // --post-rate N: one connection posting N messages a second (0: none) beside the readers.
        let wcounts = Counts()
        let writer =
            if postRate > 0 then
                let who = posters[0]
                task {
                    try
                        do! poster port (fun () -> postRequest room who) (1000 / postRate) wcounts stop.Token
                    with e ->
                        eprintfn "poster failed: %s" (e.Message.Split('\n')[0])
                } :> Task
            else Task.CompletedTask
        Thread.Sleep 300
        let ok0, c0, a0 = Volatile.Read(&counts.Ok), cpu (), GC.GetTotalAllocatedBytes false
        let sw = Stopwatch.StartNew()
        Thread.Sleep(TimeSpan.FromSeconds seconds)
        let ok1, c1, a1 = Volatile.Read(&counts.Ok), cpu (), GC.GetTotalAllocatedBytes false
        let el = sw.Elapsed.TotalSeconds
        stop.Cancel()
        (try Task.WaitAll(Array.append tasks [| writer |], 5000) |> ignore with _ -> ())
        if postRate > 0 then eprintfn "  %s: %d posts answered, %d other" variant wcounts.Ok wcounts.Bad
        let n = float (ok1 - ok0)
        let all = Campfire.Db.WriterStats.All
        if all.Restarts > 0L then eprintfn "  %s c=%d: WAL restarts so far %d, longest %d ms, deferred %d" variant conc all.Restarts (all.LongestRestartUs / 1000L) all.Deferrals
        if counts.Slow > 0L then eprintfn "  %s c=%d: %d answers over 100 ms, slowest %d ms" variant conc counts.Slow (counts.MaxUs / 1000L)
        n / el, (c1 - c0).TotalMilliseconds * 1000.0 / n, float (a1 - a0) / n / 1024.0, counts.Bad
    // The copy grows by every post; it goes when the run ends.
    AppDomain.CurrentDomain.ProcessExit.Add(fun _ -> try Directory.Delete(dir, true) with _ -> ())
    for conc in concs do
        run variants[0] conc warm |> ignore
        let results = Dictionary<string, ResizeArray<float * float * float>>()
        for _ in 1..rounds do
            for v in variants do
                let rate, us, kb, bad = run v conc secs
                if bad > 0L then eprintfn "  %s: %d non-2xx" v bad
                if not (results.ContainsKey v) then results[v] <- ResizeArray()
                results[v].Add((rate, us, kb))
        for v in variants do
            let rs = results[v]
            let med (f: float * float * float -> float) = (rs |> Seq.map f |> Seq.sort |> Array.ofSeq)[rs.Count / 2]
            printfn "c=%-3d %-40s %8.0f answers/s  %7.1f us CPU/answer  %7.1f KB/answer   [cpu %s]" conc v (med (fun (a, _, _) -> a)) (med (fun (_, b, _) -> b)) (med (fun (_, _, c) -> c)) (String.Join(" ", rs |> Seq.map (fun (_, b, _) -> b.ToString("0"))))
    // POST_MICRO_KEEP=DIR: the database, its WAL and index as the last window left them (bench/lib/walmix.py reads them).
    match Environment.GetEnvironmentVariable "POST_MICRO_KEEP" with
    | null | "" -> ()
    | keep ->
        Directory.CreateDirectory keep |> ignore
        for f in [ "production.sqlite3"; "production.sqlite3-wal"; "production.sqlite3-shm" ] do
            let from = Path.Combine(dir, "db", f)
            if File.Exists from then File.Copy(from, Path.Combine(keep, f), true)
        eprintfn "kept the database in %s" keep
    0
