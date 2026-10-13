#!/usr/bin/env python3
"""Where a saturated fan-out's server CPU goes, from `bench/cable/perf`'s kept call chains (unit R4.2 plan).

    KEEP_SCRIPT=1 bench/cable/perf --app oncrack --clients 1000 --out DIR    # inside colima
    python3 bench/results/oncrack-r4-fanout-plan/breakdown.py DIR/perf.script.gz

Shares are of all samples of the app; a sample can count in several inclusive rows.
"""
import collections, gzip, re, sys

path = sys.argv[1] if len(sys.argv) > 1 else "perf.script.gz"
samples, cur = [], []
for line in gzip.open(path, "rt", errors="replace"):
    line = line.rstrip("\n")
    if not line.strip():
        if cur:
            samples.append(cur)
            cur = []
        continue
    if not line.startswith((" ", "\t")):
        cur = [line]
        continue
    cur.append(re.sub(r"^\s*[0-9a-f]+\s+", "", line.strip()))
if cur:
    samples.append(cur)
n = len(samples)

inclusive = {
    "cable connection loop (Connection.run)": r"Connection\+run@",
    "  Writer.Send (frames to the socket)": r"Socket\+Writer::Send",
    "    Memmove into the pooled send buffer": None,
    "    the send syscall (SystemNative_Send)": r"SystemNative_Send|__syscall_cancel",
    "  drain (reading the rings)": r"Connection::drain",
    "publishing (Group.Publish, WakeBatch, BroadcastOrder)": r"Group::Publish|WakeBatch|BroadcastOrder",
    "Wake.Set": r"Wake::Set",
    "posting: MessagesController": r"MessagesController",
    "posting: views": r"Campfire\.Views",
    "posting: db (incl. sqlite)": r"Campfire\.Db|sqlite3",
    "Kestrel HTTP (the posts)": r"Http1Connection|HttpProtocol",
    "GC": r"SVR::|WKS::|gc_heap",
    "thread pool semaphore / futex": r"LowLevelLifoSemaphore|futex",
}
count = collections.Counter()
send_kind = collections.Counter()
for s in samples:
    chain = " | ".join(s[1:])
    top = s[1] if len(s) > 1 else ""
    for name, pattern in inclusive.items():
        if pattern and re.search(pattern, chain):
            count[name] += 1
    if "Memmove" in top and re.search(r"Socket\+Writer::Send", chain):
        count["    Memmove into the pooled send buffer"] += 1
    if re.search(r"SystemNative_Send|__syscall_cancel", chain):
        if "copy_from_user" in top:
            kind = "copy_from_user (per byte)"
        elif re.search(r"do_softirq|net_rx_action|__netif_receive|tcp_v4_rcv|ip_rcv", chain):
            kind = "loopback receive softirq, charged to the sender (per skb)"
        elif re.search(r"clear_page|charge|page_counter|rmqueue|prep_compound|alloc_pages|free_unref|__alloc_skb|kmalloc|page_frag", chain):
            kind = "page and skb allocation, memcg charge (per byte, mostly)"
        elif re.search(r"tcp_write_xmit|__tcp_transmit|ip_output|dev_queue_xmit", chain):
            kind = "transmit path (per skb)"
        else:
            kind = "the rest of the syscall: entry, lock_sock, tcp_sendmsg bookkeeping (per send)"
        send_kind[kind] += 1

print(f"samples {n}\n\ninclusive:")
for name in inclusive:
    print(f"  {100 * count[name] / n:5.1f}%  {name}")
print("\nthe send syscall, by kind (shares of all samples):")
for kind, v in send_kind.most_common():
    print(f"  {100 * v / n:5.1f}%  {kind}")
