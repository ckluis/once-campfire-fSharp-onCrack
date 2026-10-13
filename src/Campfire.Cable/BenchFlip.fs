namespace Campfire.Cable

open System

/// Benches only (unit R5.3): with `CAMPFIRE_CABLE_FLIP_FILE` set, a connection reads the file when it starts and takes `key=value` lines from
/// it ("order=stream": a stream at a time; "batch=N": the write batch; "log=ring": groups made from then on are rounds 1-4's rings), so one running server can alternate settings by load generator run,
/// seconds apart, on a host whose speed drifts ("hold=US": `BroadcastOrder`'s hold, read at most every 20 ms). Unset (the default) it reads nothing.
module BenchFlip =
    let private path = Environment.GetEnvironmentVariable "CAMPFIRE_CABLE_FLIP_FILE"

    /// Whether a flip file is set.
    let enabled = not (isNull path)

    /// The value of `key` in the flip file now, or null: no file set, no such line, or the file could not be read.
    let get (key: string) : string | null =
        match path with
        | null -> null
        | path ->
            try
                let prefix = key + "="
                IO.File.ReadAllLines path
                |> Array.tryPick (fun line ->
                    let line = line.Trim()
                    if line.StartsWith(prefix, StringComparison.Ordinal) then Some(line.Substring prefix.Length) else None)
                |> Option.toObj
            with _ ->
                null
