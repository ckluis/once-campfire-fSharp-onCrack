// onCrack (R2.5): where the start-up time goes. `CAMPFIRE_BOOT_LOG=1` writes `boot: N ms <what>` to stderr at the milestones below, N being
// the time since the process started (its start time in /proc, so the runtime's own start-up counts). Off unless the variable is set.
namespace Campfire.Kit

open System
open System.Diagnostics

module BootLog =
    let private enabled = not (String.IsNullOrEmpty(Environment.GetEnvironmentVariable "CAMPFIRE_BOOT_LOG"))

    let mark (what: string) : unit =
        if enabled then
            let since = DateTime.Now - Process.GetCurrentProcess().StartTime
            eprintfn "boot: %d ms %s" (int since.TotalMilliseconds) what
