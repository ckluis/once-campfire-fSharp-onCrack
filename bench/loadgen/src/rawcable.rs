//! The raw Action Cable client (`loadgen cable --client raw`, the default since R4.1): every connection is a non-blocking socket in
//! one of a few epoll loops, with no WebSocket library. It reads into one big buffer per loop, walks the frames by their headers,
//! answers pings, and looks only for what the suite validates: each subscription's confirmation, and the `bmk<seq>z` marker of each
//! posted message, once per client. What it leaves out against the tungstenite client: the UTF-8 check of every frame, a
//! `String` per frame, a task wake-up per frame, and a lock per receipt. Round 2 left the 1,000-client point at 3.85 of the load
//! generator's 4 cores with the tungstenite client, so the number measured the client. The clients are still honest ones: they
//! complete the handshake, subscribe, answer every ping with a pong echoing it, and count a message only for a client that saw it.
//!
//! Bookkeeping is per loop and written by one thread only (a `store`, never a read-modify-write on shared lines): for each
//! sequence number the receipts so far and the time of the last one; the main thread reads them to see whether a message reached
//! every client. A client's seen-set is a sliding bitmap of the last 16,384 sequence numbers.

use std::collections::VecDeque;
use std::io::{ErrorKind, Read, Write};
use std::net::{IpAddr, SocketAddr};
use std::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use hdrhistogram::Histogram;
use mio::net::TcpStream;
use mio::{Events, Interest, Poll, Token};

/// Sequence numbers the bookkeeping tracks (a message posted past it would not be counted, so posters stop short of it).
pub const RAW_SEQ_CAP: usize = 1 << 20;


/// `LOADGEN_DUMP=FILE`: the first frame that carries a marker, written there (to see where in a frame the marker sits).
static DUMPED: AtomicBool = AtomicBool::new(false);

fn dump_path() -> Option<&'static str> {
    static PATH: std::sync::OnceLock<Option<String>> = std::sync::OnceLock::new();
    PATH.get_or_init(|| std::env::var("LOADGEN_DUMP").ok()).as_deref()
}

fn zeroed<T>(n: usize) -> Box<[T]> {
    // SAFETY: only used for the atomic integers below, for which all-zero bytes are a valid value.
    unsafe { Box::<[T]>::new_zeroed_slice(n).assume_init() }
}

/// What one loop counts. Only its own thread writes it.
pub struct RawStats {
    count: Box<[AtomicU32]>,
    last: Box<[AtomicU64]>,
    pub receipts: AtomicU64,
    reads: AtomicU64,
    bytes: AtomicU64,
    frames: AtomicU64,
    pings: AtomicU64,
    odd: AtomicU64,
    overflow: AtomicU64,
    unsent: AtomicU64,
    /// Connections that ended after their subscriptions were confirmed (the server closes one whose ring it lapped).
    closed_midrun: AtomicU64,
    /// Per-client latency, µs, by phase (0 paced, 1 saturated).
    pub hists: Mutex<[Histogram<u64>; 2]>,
}

pub struct RawShared {
    pub start: Instant,
    /// When each message was posted: nanoseconds since `start`, plus one (zero: not posted).
    sent: Box<[AtomicU64]>,
    pub phase: AtomicUsize,
    pub stats: Vec<Arc<RawStats>>,
}

impl RawShared {
    pub fn new(threads: usize, hist: impl Fn() -> Histogram<u64>) -> Self {
        let stats = (0..threads)
            .map(|_| {
                Arc::new(RawStats {
                    count: zeroed(RAW_SEQ_CAP),
                    last: zeroed(RAW_SEQ_CAP),
                    receipts: AtomicU64::new(0),
                    reads: AtomicU64::new(0),
                    bytes: AtomicU64::new(0),
                    frames: AtomicU64::new(0),
                    pings: AtomicU64::new(0),
                    odd: AtomicU64::new(0),
                    overflow: AtomicU64::new(0),
                    unsent: AtomicU64::new(0),
                    closed_midrun: AtomicU64::new(0),
                    hists: Mutex::new([hist(), hist()]),
                })
            })
            .collect();
        RawShared { start: Instant::now(), sent: zeroed(RAW_SEQ_CAP), phase: AtomicUsize::new(0), stats }
    }

    pub fn mark_sent(&self, seq: u64, t0: Instant) {
        if (seq as usize) < RAW_SEQ_CAP {
            self.sent[seq as usize].store(t0.duration_since(self.start).as_nanos() as u64 + 1, Ordering::Relaxed);
        }
    }

    pub fn sent_at(&self, seq: u64) -> Instant {
        self.start + Duration::from_nanos(self.sent[seq as usize].load(Ordering::Relaxed).saturating_sub(1))
    }

    /// How many clients have received message `seq`.
    pub fn received(&self, seq: u64) -> usize {
        if seq as usize >= RAW_SEQ_CAP {
            return 0;
        }
        self.stats.iter().map(|w| w.count[seq as usize].load(Ordering::Relaxed) as usize).sum()
    }

    /// Clients that have received `seq`, and the time of the last receipt (ns since `start`).
    pub fn totals(&self, seq: u64) -> (usize, u64) {
        if seq as usize >= RAW_SEQ_CAP {
            return (0, 0);
        }
        let n = self.received(seq);
        let t = self.stats.iter().map(|w| w.last[seq as usize].load(Ordering::Relaxed)).max().unwrap_or(0);
        (n, t)
    }

    /// Totals for the result's `client` object.
    pub fn summary(&self) -> serde_json::Value {
        let sum = |f: fn(&RawStats) -> &AtomicU64| self.stats.iter().map(|w| f(w).load(Ordering::Relaxed)).sum::<u64>();
        serde_json::json!({
            "kind": "raw",
            "threads": self.stats.len(),
            "reads": sum(|w| &w.reads),
            "read_bytes": sum(|w| &w.bytes),
            "frames": sum(|w| &w.frames),
            "pings_answered": sum(|w| &w.pings),
            "odd_frames": sum(|w| &w.odd),
            "markers_past_cap": sum(|w| &w.overflow),
            "receipts_without_post_time": sum(|w| &w.unsent),
            "closed_midrun": sum(|w| &w.closed_midrun),
        })
    }
}

/// The last 16,384 sequence numbers a client has seen, as a sliding bitmap. A number older than the window counts as seen.
struct SeenWindow {
    base: u64,
    words: VecDeque<u64>,
}

const WINDOW_WORDS: u64 = 256;

impl SeenWindow {
    fn new() -> Self {
        SeenWindow { base: 0, words: VecDeque::new() }
    }

    /// True when `seq` was not in the window.
    fn insert(&mut self, seq: u64) -> bool {
        let w = seq >> 6;
        if w < self.base {
            return false;
        }
        let mut rel = w - self.base;
        if rel >= WINDOW_WORDS {
            let new_base = w - (WINDOW_WORDS / 2 - 1);
            let drop = (new_base - self.base) as usize;
            if drop >= self.words.len() {
                self.words.clear();
            } else {
                self.words.drain(..drop);
            }
            self.base = new_base;
            rel = w - new_base;
        }
        let rel = rel as usize;
        if self.words.len() <= rel {
            self.words.resize(rel + 1, 0);
        }
        let bit = 1u64 << (seq & 63);
        let fresh = self.words[rel] & bit == 0;
        self.words[rel] |= bit;
        fresh
    }
}

#[derive(PartialEq, Clone, Copy)]
enum Stage {
    Connecting,
    Head,
    Open,
}

struct Conn {
    stream: TcpStream,
    stage: Stage,
    /// Bytes waiting to be written (a pong, the subscriptions) from `out_at`.
    out: Vec<u8>,
    out_at: usize,
    /// The start of a frame that is not complete yet.
    rest: Vec<u8>,
    seen: SeenWindow,
    confirms: usize,
}

pub struct RawConfig {
    pub addr: String,
    pub request: Vec<u8>,
    /// Every subscribe command, as client frames, back to back.
    pub subscribes: Vec<u8>,
    pub nsubs: usize,
    pub handshakes_in_flight: usize,
    /// How much of a frame's end is searched for its marker before the whole frame is (0: the whole frame).
    pub tail_window: usize,
}

pub struct Counters {
    pub confirmed: Arc<AtomicUsize>,
    pub connected: Arc<AtomicUsize>,
    pub failed: Arc<AtomicUsize>,
    pub stop: Arc<AtomicBool>,
}

/// A client's pong: masked, echoing the ping's payload (at most 125 bytes).
fn pong(payload: &[u8]) -> Vec<u8> {
    let mask = [0x1f, 0x7a, 0x93, 0xc4];
    let mut frame = vec![0x8A, 0x80 | payload.len() as u8];
    frame.extend_from_slice(&mask);
    frame.extend(payload.iter().enumerate().map(|(i, b)| b ^ mask[i % 4]));
    frame
}

fn flush(c: &mut Conn) -> Result<(), ()> {
    while c.out_at < c.out.len() {
        match c.stream.write(&c.out[c.out_at..]) {
            Ok(0) => return Err(()),
            Ok(n) => c.out_at += n,
            Err(e) if e.kind() == ErrorKind::WouldBlock => return Ok(()),
            Err(e) if e.kind() == ErrorKind::Interrupted => {}
            Err(_) => return Err(()),
        }
    }
    c.out.clear();
    c.out_at = 0;
    Ok(())
}

struct Worker<'a> {
    cfg: &'a RawConfig,
    counters: &'a Counters,
    shared: &'a RawShared,
    stats: &'a RawStats,
    finder: memchr::memmem::Finder<'static>,
    confirm_finder: memchr::memmem::Finder<'static>,
    rbuf: Vec<u8>,
    now_ns: u64,
    phase: usize,
    receipts: u64,
    handshaking: usize,
    /// Set by a read that stopped inside a frame that is bigger than the buffer.
    need: usize,
}

impl Worker<'_> {
    /// A text frame's payload: a subscription's confirmation, or the markers of the messages it carries.
    fn payload(&mut self, c: &mut Conn, payload: &[u8], hist: &mut Histogram<u64>) {
        if c.confirms < self.cfg.nsubs && self.confirm_finder.find(payload).is_some() {
            c.confirms += 1;
            if c.confirms == self.cfg.nsubs {
                self.counters.confirmed.fetch_add(1, Ordering::Relaxed);
            }
            return;
        }
        if let Some(path) = dump_path() {
            if self.finder.find(payload).is_some() && !DUMPED.swap(true, Ordering::Relaxed) {
                let _ = std::fs::write(path, payload);
            }
        }
        // The profile of round 4's first raw client put 28% of its CPU in the substring search over 10 KB frames, and a message's
        // text sits about 1 KB from the end of its frame. So look in the last `tail_window` bytes first (4,096 by default; `--tail-window 0` searches whole frames), and in the whole frame only
        // when that has no complete marker (a marker cut by the window's edge, or sitting early in a frame). A frame that carries
        // two messages, one early and one late, would be counted for the late one only: this suite posts one message per frame, and
        // a miscount can only make a message look undelivered, never delivered.
        let tail = if self.cfg.tail_window == 0 { 0 } else { payload.len().saturating_sub(self.cfg.tail_window) };
        let mut found = if tail > 0 { self.markers(c, &payload[tail..], hist) } else { 0 };
        if found == 0 {
            found = self.markers(c, payload, hist);
        }
        let _ = found;
    }

    /// Records the markers in `hay`; returns how many complete ones it held (new to this client or not).
    fn markers(&mut self, c: &mut Conn, hay: &[u8], hist: &mut Histogram<u64>) -> usize {
        let mut found = 0;
        for at in self.finder.find_iter(hay) {
            let digits = &hay[at + 3..];
            let n = digits.iter().take_while(|b| b.is_ascii_digit()).count();
            if n == 0 || n > 18 || digits.get(n) != Some(&b'z') {
                continue;
            }
            found += 1;
            let seq = digits[..n].iter().fold(0u64, |a, d| a * 10 + (d - b'0') as u64);
            if seq as usize >= RAW_SEQ_CAP {
                self.stats.overflow.fetch_add(1, Ordering::Relaxed);
                continue;
            }
            if !c.seen.insert(seq) {
                continue;
            }
            self.receipts += 1;
            let k = &self.stats.count[seq as usize];
            k.store(k.load(Ordering::Relaxed) + 1, Ordering::Relaxed);
            self.stats.last[seq as usize].store(self.now_ns, Ordering::Relaxed);
            let sent = self.shared.sent[seq as usize].load(Ordering::Relaxed);
            if sent != 0 {
                hist.record(((self.now_ns + 1).saturating_sub(sent) / 1000).max(1)).ok();
            } else {
                self.stats.unsent.fetch_add(1, Ordering::Relaxed);
            }
        }
        found
    }

    /// Walks the complete frames of `buf`; returns how many bytes it used.
    fn frames(&mut self, c: &mut Conn, buf: &[u8], hist: &mut Histogram<u64>) -> Result<usize, ()> {
        let mut pos = 0;
        let mut frames = 0u64;
        while buf.len() - pos >= 2 {
            let (b0, b1) = (buf[pos], buf[pos + 1]);
            let mut len = (b1 & 0x7f) as usize;
            let mut header = 2;
            if len == 126 {
                if buf.len() - pos < 4 {
                    break;
                }
                len = u16::from_be_bytes([buf[pos + 2], buf[pos + 3]]) as usize;
                header = 4;
            } else if len == 127 {
                if buf.len() - pos < 10 {
                    break;
                }
                len = u64::from_be_bytes(buf[pos + 2..pos + 10].try_into().unwrap()) as usize;
                header = 10;
            }
            if b1 & 0x80 != 0 {
                // A server never masks.
                return Err(());
            }
            let total = header + len;
            if buf.len() - pos < total {
                self.need = total;
                break;
            }
            let payload = &buf[pos + header..pos + total];
            match b0 & 0x0f {
                0x1 => {
                    if b0 & 0x80 == 0 {
                        self.stats.odd.fetch_add(1, Ordering::Relaxed);
                    }
                    self.payload(c, payload, hist);
                }
                0x9 => {
                    self.stats.pings.fetch_add(1, Ordering::Relaxed);
                    c.out.extend_from_slice(&pong(&payload[..payload.len().min(125)]));
                    flush(c)?;
                }
                0x8 => return Err(()),
                0xA => {}
                _ => {
                    self.stats.odd.fetch_add(1, Ordering::Relaxed);
                }
            }
            pos += total;
            frames += 1;
        }
        self.stats.frames.fetch_add(frames, Ordering::Relaxed);
        Ok(pos)
    }

    /// Reads what the socket has (edge-triggered: until it would block, or a read comes back short).
    fn read(&mut self, c: &mut Conn, hist: &mut Histogram<u64>) -> Result<(), ()> {
        loop {
            let have = c.rest.len();
            if have > 0 {
                self.rbuf[..have].copy_from_slice(&c.rest);
                c.rest.clear();
            }
            let want = self.rbuf.len() - have;
            let n = match c.stream.read(&mut self.rbuf[have..]) {
                Ok(0) => return Err(()),
                Ok(n) => n,
                Err(e) if e.kind() == ErrorKind::WouldBlock => return Ok(()),
                Err(e) if e.kind() == ErrorKind::Interrupted => continue,
                Err(_) => return Err(()),
            };
            self.stats.reads.fetch_add(1, Ordering::Relaxed);
            self.stats.bytes.fetch_add(n as u64, Ordering::Relaxed);
            self.now_ns = self.shared.start.elapsed().as_nanos() as u64;
            // The buffer moves out so that `frames` can borrow `self` too.
            let buf = std::mem::take(&mut self.rbuf);
            let total = have + n;
            let mut pos = 0;
            let mut result = Ok(());
            if c.stage == Stage::Head {
                match buf[..total].windows(4).position(|w| w == b"\r\n\r\n") {
                    Some(end) => {
                        if !buf.starts_with(b"HTTP/1.1 101") {
                            result = Err(());
                        } else {
                            pos = end + 4;
                            c.stage = Stage::Open;
                            self.handshaking -= 1;
                            self.counters.connected.fetch_add(1, Ordering::Relaxed);
                            c.out.extend_from_slice(&self.cfg.subscribes);
                            result = flush(c);
                        }
                    }
                    None if total > 16 * 1024 => result = Err(()),
                    None => {}
                }
            }
            if result.is_ok() && c.stage == Stage::Open {
                self.need = 0;
                match self.frames(c, &buf[pos..total], hist) {
                    Ok(used) => pos += used,
                    Err(()) => result = Err(()),
                }
            }
            if result.is_ok() && pos < total {
                c.rest.extend_from_slice(&buf[pos..total]);
            }
            self.rbuf = buf;
            result?;
            // A frame bigger than the buffer: grow it.
            if self.need > self.rbuf.len() {
                let size = self.need.next_power_of_two();
                self.rbuf.resize(size, 0);
            }
            // A short read has drained a stream socket.
            if n < want {
                return Ok(());
            }
        }
    }
}

/// EINPROGRESS: 115 on Linux, 36 on macOS.
fn libc_einprogress() -> i32 {
    if cfg!(target_os = "linux") { 115 } else { 36 }
}

fn start(poll: &Poll, conns: &mut Vec<Option<Conn>>, free: &mut Vec<usize>, cfg: &RawConfig, source: Option<IpAddr>, addr: SocketAddr) -> Result<(), ()> {
    use socket2::{Domain, Protocol, Socket, Type};
    let socket = Socket::new(Domain::IPV4, Type::STREAM, Some(Protocol::TCP)).map_err(|_| ())?;
    socket.set_tcp_nodelay(true).map_err(|_| ())?;
    socket.set_nonblocking(true).map_err(|_| ())?;
    if let Some(source) = source {
        socket.bind(&SocketAddr::new(source, 0).into()).map_err(|_| ())?;
    }
    match socket.connect(&addr.into()) {
        Ok(()) => {}
        Err(e) if e.raw_os_error() == Some(libc_einprogress()) || e.kind() == ErrorKind::WouldBlock => {}
        Err(_) => return Err(()),
    }
    let mut stream = TcpStream::from_std(socket.into());
    let slot = free.pop().unwrap_or_else(|| {
        conns.push(None);
        conns.len() - 1
    });
    poll.registry().register(&mut stream, Token(slot), Interest::READABLE | Interest::WRITABLE).map_err(|_| ())?;
    conns[slot] = Some(Conn {
        stream,
        stage: Stage::Connecting,
        out: cfg.request.clone(),
        out_at: 0,
        rest: Vec::new(),
        seen: SeenWindow::new(),
        confirms: 0,
    });
    Ok(())
}

/// One epoll loop owning `sources.len()` clients (one entry per client: the address it connects from, if any) until `stop`.
pub fn run_worker(
    cfg: Arc<RawConfig>,
    counters: Counters,
    shared: Arc<RawShared>,
    stats: Arc<RawStats>,
    sources: Vec<Option<IpAddr>>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use std::net::ToSocketAddrs;
    let addr = cfg.addr.to_socket_addrs()?.find(|a| a.is_ipv4()).ok_or("no address")?;
    let mut poll = Poll::new()?;
    let mut events = Events::with_capacity(1024);
    let mut conns: Vec<Option<Conn>> = Vec::with_capacity(sources.len());
    let mut free: Vec<usize> = Vec::new();
    let mut todo: VecDeque<Option<IpAddr>> = sources.into();
    let mut w = Worker {
        cfg: &cfg,
        counters: &counters,
        shared: &shared,
        stats: &stats,
        finder: memchr::memmem::Finder::new(b"bmk").into_owned(),
        confirm_finder: memchr::memmem::Finder::new(b"confirm_subscription").into_owned(),
        rbuf: vec![0u8; 256 * 1024],
        now_ns: 0,
        phase: 0,
        receipts: 0,
        handshaking: 0,
        need: 0,
    };
    loop {
        while w.handshaking < cfg.handshakes_in_flight {
            let Some(source) = todo.pop_front() else { break };
            if start(&poll, &mut conns, &mut free, &cfg, source, addr).is_ok() {
                w.handshaking += 1;
            } else {
                counters.failed.fetch_add(1, Ordering::Relaxed);
            }
        }
        if counters.stop.load(Ordering::Relaxed) {
            break;
        }
        if let Err(e) = poll.poll(&mut events, Some(Duration::from_millis(20))) {
            if e.kind() == ErrorKind::Interrupted {
                continue;
            }
            return Err(e.into());
        }
        if events.is_empty() {
            continue;
        }
        w.phase = shared.phase.load(Ordering::Relaxed);
        let mut hists = stats.hists.lock().unwrap();
        for ev in events.iter() {
            let slot = ev.token().0;
            let Some(c) = conns[slot].as_mut() else { continue };
            let mut result = Ok(());
            if c.stage == Stage::Connecting {
                if ev.is_error() {
                    result = Err(());
                } else if ev.is_writable() {
                    match c.stream.take_error() {
                        Ok(None) => match c.stream.peer_addr() {
                            Ok(_) => {
                                c.stage = Stage::Head;
                                result = flush(c);
                            }
                            Err(e) if e.kind() == ErrorKind::NotConnected => {}
                            Err(_) => result = Err(()),
                        },
                        _ => result = Err(()),
                    }
                }
            } else if ev.is_writable() {
                result = flush(c);
            }
            if result.is_ok() && c.stage != Stage::Connecting && (ev.is_readable() || ev.is_read_closed()) {
                let hist = &mut hists[w.phase];
                result = w.read(c, hist);
            }
            if result.is_err() {
                let c = conns[slot].take().unwrap();
                let mut stream = c.stream;
                let _ = poll.registry().deregister(&mut stream);
                if c.stage != Stage::Open {
                    w.handshaking -= 1;
                }
                if c.confirms < cfg.nsubs {
                    counters.failed.fetch_add(1, Ordering::Relaxed);
                } else {
                    stats.closed_midrun.fetch_add(1, Ordering::Relaxed);
                }
                free.push(slot);
            }
        }
        drop(hists);
        stats.receipts.fetch_add(std::mem::take(&mut w.receipts), Ordering::Relaxed);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::TcpListener;

    fn hist() -> Histogram<u64> {
        Histogram::new_with_bounds(1, 120_000_000, 3).unwrap()
    }

    fn text_frame(payload: &[u8]) -> Vec<u8> {
        let mut f = vec![0x81];
        match payload.len() {
            n if n < 126 => f.push(n as u8),
            n if n < 65536 => {
                f.push(126);
                f.extend_from_slice(&(n as u16).to_be_bytes());
            }
            n => {
                f.push(127);
                f.extend_from_slice(&(n as u64).to_be_bytes());
            }
        }
        f.extend_from_slice(payload);
        f
    }

    #[test]
    fn seen_window_counts_each_sequence_once() {
        let mut w = SeenWindow::new();
        assert!(w.insert(1));
        assert!(!w.insert(1));
        assert!(w.insert(3));
        assert!(w.insert(2));
        assert!(!w.insert(2));
        // Far ahead: the window slides and what fell out of it counts as seen.
        assert!(w.insert(100_000));
        assert!(!w.insert(100_000));
        assert!(!w.insert(1));
        assert!(w.insert(99_999));
        assert!(!w.insert(99_999));
        for seq in 100_001..130_000 {
            assert!(w.insert(seq), "{seq}");
        }
        assert!(w.words.len() <= WINDOW_WORDS as usize);
    }

    /// A server in a thread: each connection gets the 101, `nsubs` confirmations, a ping (and must answer it with the same payload),
    /// then `messages` frames of about 10 KB with the marker 1 KB from the end (plus an unmarked small frame and one marker early in
    /// a frame), written in uneven pieces so that reads cut headers, payloads and markers. Returns the pongs it saw.
    fn serve(listener: TcpListener, nsubs: usize, messages: u64) -> std::thread::JoinHandle<usize> {
        std::thread::spawn(move || {
            let mut conns = Vec::new();
            let mut pongs = 0;
            let mut rng = 12345u64;
            let mut next = move || {
                rng = rng.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                (rng >> 33) as usize
            };
            while conns.len() < 3 {
                let (mut s, _) = listener.accept().unwrap();
                s.set_nodelay(true).unwrap();
                let mut head = Vec::new();
                let mut b = [0u8; 1];
                while !head.ends_with(b"\r\n\r\n") {
                    s.read_exact(&mut b).unwrap();
                    head.push(b[0]);
                }
                let mut out = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n\r\n".to_vec();
                for _ in 0..nsubs {
                    out.extend(text_frame(br#"{"identifier":"x","type":"confirm_subscription"}"#));
                }
                out.extend_from_slice(&[0x89, 8, 1, 2, 3, 4, 5, 6, 7, 8]);
                for seq in 1..=messages {
                    let mut body = vec![b'.'; 10_000];
                    let marker = format!("fanout bmk{seq}z");
                    let at = if seq % 17 == 0 { 100 } else { body.len() - 1037 };
                    body[at..at + marker.len()].copy_from_slice(marker.as_bytes());
                    out.extend(text_frame(&body));
                    out.extend(text_frame(br#"{"message":"unread"}"#));
                }
                // The same message twice on one connection must still count once.
                out.extend(text_frame(b"x bmk1z y"));
                let mut at = 0;
                while at < out.len() {
                    let n = (1 + next() % 7000).min(out.len() - at);
                    s.write_all(&out[at..at + n]).unwrap();
                    at += n;
                }
                conns.push(s);
            }
            for s in &mut conns {
                s.set_read_timeout(Some(Duration::from_secs(5))).unwrap();
                let mut got = vec![0u8; 14];
                if s.read_exact(&mut got).is_ok() && got[0] == 0x8A && got[1] == 0x88 {
                    let m = [got[2], got[3], got[4], got[5]];
                    let payload: Vec<u8> = got[6..14].iter().enumerate().map(|(i, b)| b ^ m[i % 4]).collect();
                    if payload == [1, 2, 3, 4, 5, 6, 7, 8] {
                        pongs += 1;
                    }
                }
            }
            pongs
        })
    }

    #[test]
    fn counts_every_message_once_over_cut_reads_and_answers_pings() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let addr = listener.local_addr().unwrap().to_string();
        let (nsubs, messages) = (3usize, 400u64);
        let server = serve(listener, nsubs, messages);
        let shared = Arc::new(RawShared::new(2, hist));
        let counters = || Counters {
            confirmed: Arc::new(AtomicUsize::new(0)),
            connected: Arc::new(AtomicUsize::new(0)),
            failed: Arc::new(AtomicUsize::new(0)),
            stop: Arc::new(AtomicBool::new(false)),
        };
        let first = counters();
        let (confirmed, failed, stop) = (first.confirmed.clone(), first.failed.clone(), first.stop.clone());
        let cfg = Arc::new(RawConfig {
            addr,
            request: b"GET /cable HTTP/1.1\r\nHost: x\r\n\r\n".to_vec(),
            subscribes: Vec::new(),
            nsubs,
            handshakes_in_flight: 2,
            tail_window: 4096,
        });
        // Three clients over two loops.
        let mut threads = Vec::new();
        for (t, n) in [(0usize, 2usize), (1, 1)] {
            let c = Counters {
                confirmed: confirmed.clone(),
                connected: first.connected.clone(),
                failed: failed.clone(),
                stop: stop.clone(),
            };
            let (cfg, shared, stats) = (cfg.clone(), shared.clone(), shared.stats[t].clone());
            threads.push(std::thread::spawn(move || run_worker(cfg, c, shared, stats, vec![None; n]).unwrap()));
        }
        let until = Instant::now() + Duration::from_secs(20);
        let everything = |shared: &RawShared| (1..=messages).all(|s| shared.received(s) == 3);
        while !everything(&shared) && Instant::now() < until {
            std::thread::sleep(Duration::from_millis(20));
        }
        std::thread::sleep(Duration::from_millis(200));
        stop.store(true, Ordering::Relaxed);
        for t in threads {
            t.join().unwrap();
        }
        assert_eq!(confirmed.load(Ordering::Relaxed), 3);
        assert_eq!(failed.load(Ordering::Relaxed), 0);
        for s in 1..=messages {
            assert_eq!(shared.received(s), 3, "message {s}");
        }
        assert_eq!(shared.received(messages + 1), 0);
        assert_eq!(server.join().unwrap(), 3, "every client answered the ping with its payload");
        let receipts: u64 = shared.stats.iter().map(|w| w.receipts.load(Ordering::Relaxed)).sum();
        assert_eq!(receipts, 3 * messages);
    }
}
