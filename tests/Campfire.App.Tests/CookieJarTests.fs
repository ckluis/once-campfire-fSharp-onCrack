// onCrack R4.0: the test browser's cookie jar (`Support.setCookieDeletes`). It dropped a cookie when "1970" appeared anywhere in the
// `Set-Cookie` header, and the session cookie's hex digest holds that run of digits about once in 1,800 refreshes: a signed-in browser
// was then signed out (the verifier's A7, one failure in 540 rounds, never in the app). The jar must read the attributes only.
module Campfire.App.Tests.CookieJarTests

open System
open Xunit
open Campfire.RailsCompat
open Campfire.App.Tests.Support

let private header (name: string) (raw: string) (expires: DateTimeOffset) : string =
    let date = expires.UtcDateTime.ToString("R", Globalization.CultureInfo.InvariantCulture)
    $"{name}={Cookies.escape raw}; path=/; expires={date}; httponly; samesite=lax"

[<Fact>]
let ``a signed cookie whose text holds 1970 stays in the jar`` () =
    let secrets = Secrets.create "test-secret-key-base"
    let now = DateTimeOffset(2026, 10, 9, 12, 0, 0, TimeSpan.Zero)
    let expires = Cookies.permanentExpiresAt now
    // The same cookie as the app writes (`cookies.signed.permanent`), its expiry stepping by milliseconds as the clock does, until one
    // has the digits in its hex digest. About one in 1,800 does, so this takes a few thousand signatures.
    let found =
        Seq.initInfinite id
        |> Seq.truncate 200_000
        |> Seq.map (fun i -> header "session_token" (Cookies.sign secrets "session_token" "wPNZuFSHzdqx8Dtbs3AzGUVk" (Some(expires.AddMilliseconds(float i)))) expires)
        |> Seq.tryFind (fun h -> h.Contains "1970")
    match found with
    | None -> failwith "no signed cookie with 1970 in 200,000 tries"
    | Some cookie ->
        Assert.DoesNotContain("expires=Thu, 01 Jan 1970", cookie)
        Assert.False(setCookieDeletes cookie, cookie)

[<Fact>]
let ``a cookie the app deletes leaves the jar`` () =
    Assert.True(setCookieDeletes "session_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT")
    Assert.True(setCookieDeletes "session_token=; max-age=0; path=/")
    Assert.True(setCookieDeletes "_campfire_session=abc; path=/; max-age=0")
    Assert.True(setCookieDeletes "last_room=5; path=/; expires=Mon, 01 Jan 2024 00:00:00 GMT")

[<Fact>]
let ``a live cookie stays`` () =
    Assert.False(setCookieDeletes "session_token=abc; path=/; expires=Wed, 10 Oct 2046 02:37:14 GMT; httponly; samesite=lax")
    Assert.False(setCookieDeletes "last_room=486777696; path=/; samesite=lax")
    Assert.False(setCookieDeletes "x=1970; path=/; max-age=3600")
    Assert.False(setCookieDeletes "x=--1970--; path=/")
