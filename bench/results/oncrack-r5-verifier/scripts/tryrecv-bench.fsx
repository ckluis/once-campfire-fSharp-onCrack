// Ns per Subscriber.TryRecv: 1,000 subscribers of one group drain 256 published frames, round after round (both builds, alternated).
#r "__DLL__"
open System
open Campfire.Cable
open Campfire.Cable.Socket
let hub = Hub(256)
let subs = [| for _ in 1..1000 -> hub.Subscribe("room", null, Wake()) |]
let payload = Text.Encoding.UTF8.GetBytes(String('x', 1400))
let drain () =
    let mutable n = 0
    for s in subs do
        let mutable frame = Unchecked.defaultof<Frame>
        while s.TryRecv(&frame) = RecvStatus.Got do
            n <- n + 1
    n
let round () =
    for _ in 1..256 do
        hub.Broadcast("room", ReadOnlySpan payload) |> ignore
    let t = Diagnostics.Stopwatch.GetTimestamp()
    let n = drain ()
    let dt = Diagnostics.Stopwatch.GetElapsedTime t
    hub.Trim()
    dt.TotalNanoseconds / float n
for _ in 1..60 do round () |> ignore
let xs = [| for _ in 1..200 -> round () |] |> Array.sort
printfn "%s median %.2f ns  p25 %.2f  p75 %.2f" (Environment.GetEnvironmentVariable "ARM") xs[100] xs[50] xs[150]
