// onCrack R2.4: when an app request may run on the event thread it arrived on.
module Campfire.Kit.Tests.EventThreadWatchTests

open System.Threading
open Xunit
open Campfire.Kit

let private onFreshThread (f: unit -> 'a) : 'a =
    let mutable result = Unchecked.defaultof<'a>
    let t = Thread((fun () -> result <- f ()))
    t.Start()
    t.Join()
    result

[<Fact>]
let ``the first request of a connection waits out the window, then runs in place`` () =
    onFreshThread (fun () ->
        let a = obj ()
        Assert.False(EventThreadWatch.SoloFor(a, 1000L, 200L))
        Assert.False(EventThreadWatch.SoloFor(a, 1199L, 200L))
        Assert.True(EventThreadWatch.SoloFor(a, 1200L, 200L))
        Assert.True(EventThreadWatch.SoloFor(a, 5000L, 200L)))

[<Fact>]
let ``another connection on the same thread starts the window again, for both`` () =
    onFreshThread (fun () ->
        let a, b = obj (), obj ()
        Assert.False(EventThreadWatch.SoloFor(a, 0L, 200L))
        Assert.True(EventThreadWatch.SoloFor(a, 300L, 200L))
        Assert.False(EventThreadWatch.SoloFor(b, 310L, 200L))
        Assert.False(EventThreadWatch.SoloFor(a, 320L, 200L))
        Assert.False(EventThreadWatch.SoloFor(b, 400L, 200L))
        Assert.True(EventThreadWatch.SoloFor(b, 600L, 200L)))

[<Fact>]
let ``a thread is judged by its own connections only`` () =
    let a = obj ()
    let first = onFreshThread (fun () -> EventThreadWatch.SoloFor(a, 0L, 200L) |> ignore; EventThreadWatch.SoloFor(a, 300L, 200L))
    // a second thread serving a different connection does not move the first thread's window, and a third starts its own
    let other = onFreshThread (fun () -> EventThreadWatch.SoloFor(obj (), 301L, 200L))
    let third = onFreshThread (fun () -> EventThreadWatch.SoloFor(a, 302L, 200L))
    Assert.True first
    Assert.False other
    Assert.False third

[<Fact>]
let ``a negative window is never solo, zero always`` () =
    onFreshThread (fun () ->
        let a = obj ()
        Assert.False(EventThreadWatch.SoloFor(a, 0L, -1L))
        Assert.False(EventThreadWatch.SoloFor(a, 9999L, -1L))
        Assert.True(EventThreadWatch.SoloFor(obj (), 0L, 0L)))

[<Fact>]
let ``cheap paths match the request path exactly`` () =
    CheapPaths.register [ "/up"; "/up.json" ]
    try
        Assert.True(CheapPaths.contains "/up")
        Assert.True(CheapPaths.contains "/up.json")
        Assert.False(CheapPaths.contains "/up/")
        Assert.False(CheapPaths.contains "/UP")
        Assert.False(CheapPaths.contains "/rooms/1")
        Assert.False(CheapPaths.contains "")
    finally
        CheapPaths.register []
