// Port of rust/crates/campfire/src/main.rs
//
// The Campfire server: controllers, channels, jobs and integrations wired over the libraries
// (`Boot.run` is app.rs's entry point). Rust's jemalloc options and `transparent_huge_pages` opt-out
// become the GC settings in the project file and `disableTransparentHugePages` here.
module Campfire.App.Program

open System
open System.Runtime.InteropServices

module private Native =
    [<DllImport("libc.so.6", EntryPoint = "prctl")>]
    extern int prctl(int option, uint64 arg2, uint64 arg3, uint64 arg4, uint64 arg5)

/// `PR_SET_THP_DISABLE` and `PR_GET_THP_DISABLE` (linux/prctl.h).
[<Literal>]
let private PrSetThpDisable = 41

[<Literal>]
let private PrGetThpDisable = 42

/// On kernels with transparent huge pages set to `always` (Debian's and Arch's default), every thread's
/// stack and each of the allocator's regions get backed by whole 2 MB pages as soon as they're touched: an
/// idle server took 160 MB on 32 cores instead of 15 MB. Nothing here is big enough to gain from huge
/// pages, so the process (and ffmpeg, which inherits it) opts out.
let disableTransparentHugePages () : unit =
    if OperatingSystem.IsLinux() then
        if Native.prctl (PrSetThpDisable, 1UL, 0UL, 0UL, 0UL) <> 0 then
            eprintfn "couldn't disable transparent huge pages: %s" (Marshal.GetLastPInvokeErrorMessage())

/// Whether `disableTransparentHugePages` took (Linux only).
let transparentHugePagesDisabled () : bool = Native.prctl (PrGetThpDisable, 0UL, 0UL, 0UL, 0UL) = 1

[<EntryPoint>]
let main argv =
    disableTransparentHugePages ()
    // onCrack (R2.3): with CAMPFIRE_INLINE (`Campfire.Kit.FrontInline`), socket completions run on the event threads too (the runtime
    // reads this once, when the first socket is made), unless the variable was given.
    if Campfire.Kit.FrontInline.mode <> Campfire.Kit.FrontInline.Off
       && isNull (Environment.GetEnvironmentVariable "DOTNET_SYSTEM_NET_SOCKETS_INLINE_COMPLETIONS") then
        Environment.SetEnvironmentVariable("DOTNET_SYSTEM_NET_SOCKETS_INLINE_COMPLETIONS", "1")
    // onCrack (R2.4): idle thread pool workers do not spin. The default of 70 normalized spins kept a worker running for about 100 us after
    // every hand-off, which at one connection was half of a post's CPU (345 -> 263 us, same req/s) and with replays answered on the event
    // threads costs nothing at 16 or 64 (bench/results/oncrack-r2-c1.md). Read by the runtime when the pool first starts, so it is set
    // before anything uses the pool; a value given to the container (DOTNET_ThreadPool_UnfairSemaphoreSpinLimit, in hex) wins.
    // Only with replays on the event threads (CAMPFIRE_INLINE, the fast path): with the pool serving every cached hit (R2.3's measurement of
    // the pool alone) a worker that sleeps between requests cost 29% at 16 connections.
    if Campfire.Kit.FrontInline.mode <> Campfire.Kit.FrontInline.Off
       && isNull (Environment.GetEnvironmentVariable "DOTNET_ThreadPool_UnfairSemaphoreSpinLimit") then
        Environment.SetEnvironmentVariable("DOTNET_ThreadPool_UnfairSemaphoreSpinLimit", "0")
    // The health check does no I/O and takes microseconds: the front server runs it on the event thread (`Campfire.Kit.CheapPaths`).
    Campfire.Kit.CheapPaths.register [ "/up"; "/up.html"; "/up.json" ]
    Boot.run argv
