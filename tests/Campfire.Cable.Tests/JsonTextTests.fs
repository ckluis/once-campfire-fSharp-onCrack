// Not in the Rust crate (which hands serde_json a &str): `JsonStringWriter` must write what
// `Json.encode (Value.String s)` writes, however the text is split up.
module Campfire.Cable.Tests.JsonTextTests

open System
open System.Text
open Xunit
open Campfire.RailsCompat
open Campfire.Cable

let private samples =
    [ ""
      "plain"
      "<b>&</b>"
      "quote \" and backslash \\ and slash /"
      "controls \u0000 \u0001 \b \f \n \r \t \u001f \u007f"
      "snowman ☃, é,    , a pair \U0001F600 end"
      String.replicate 500 "<div class=\"m\">Hi &amp; bye ☃</div>\n" ]

[<Fact>]
let ``strings are escaped as Active Support encodes them`` () =
    for sample in samples do
        Assert.Equal(Json.encode (Value.String sample), Encoding.UTF8.GetString(JsonText.encodeString sample))

[<Fact>]
let ``pieces and UTF-8 input write the same text`` () =
    for sample in samples do
        let expected = Json.encode (Value.String sample)
        use pieces = new JsonStringWriter(8)
        pieces.Begin()
        let mutable i = 0
        while i < sample.Length do
            // A split inside a surrogate pair would not be text, so pairs stay whole.
            let mutable n = min 7 (sample.Length - i)
            if n < sample.Length - i && Char.IsHighSurrogate sample[i + n - 1] then n <- n + 1
            pieces.Append(sample.AsSpan(i, n))
            i <- i + n
        pieces.End()
        Assert.Equal(expected, Encoding.UTF8.GetString pieces.Span)
        use utf8 = new JsonStringWriter()
        utf8.Begin()
        utf8.AppendUtf8(ReadOnlySpan(Encoding.UTF8.GetBytes sample))
        utf8.End()
        Assert.Equal(expected, Encoding.UTF8.GetString utf8.Span)

[<Fact>]
let ``a long text grows the buffer`` () =
    let text = String.replicate 100000 "<&>"
    Assert.Equal(Json.encode (Value.String text), Encoding.UTF8.GetString(JsonText.encodeString text))

// onCrack (unit R2.1): the compact writer leaves `<`, `>` and `&` alone; the JSON it writes must parse to the same string.

[<Fact>]
let ``compact strings parse to the same text, with only what JSON requires escaped`` () =
    for sample in samples @ [ String.replicate 50 "</script><!-- & -->"; "    line separators" ] do
        use compact = new JsonStringWriter(8, true)
        compact.Begin()
        compact.Append sample
        compact.End()
        let text = Encoding.UTF8.GetString compact.Span
        Assert.Equal(Some(Value.String sample), Json.parse (compact.Span.ToArray()))
        Assert.DoesNotContain("\\u003c", text)
        Assert.DoesNotContain("\\u003e", text)
        Assert.DoesNotContain("\\u0026", text)
        // Quotes, backslashes and control characters still are, as JSON requires.
        Assert.Equal(sample.Contains '"', text.Contains "\\\"")
        for c in text.Substring(1, text.Length - 2) do
            Assert.True(c >= ' ', $"unescaped control character {int c}")
        // And through the UTF-8 path, the same bytes.
        use utf8 = new JsonStringWriter(8, true)
        utf8.Begin()
        utf8.AppendUtf8(ReadOnlySpan(Encoding.UTF8.GetBytes sample))
        utf8.End()
        Assert.Equal(text, Encoding.UTF8.GetString utf8.Span)

[<Fact>]
let ``a compact Turbo Stream frame is smaller and decodes to the Rails frame's value`` () =
    let html = String.replicate 20 """<div class="message" data-id="1"><a href="/rooms/1?x=1&y=2">Hi & bye</a></div>"""
    let encode (compact: bool) =
        use w = new JsonStringWriter(64, compact)
        w.Begin()
        w.Append html
        w.End()
        w.ToArray()
    let rails, compact = encode false, encode true
    Assert.Equal(Json.parse rails, Json.parse compact)
    Assert.True(float compact.Length < 0.8 * float rails.Length, $"{compact.Length} vs {rails.Length}")
