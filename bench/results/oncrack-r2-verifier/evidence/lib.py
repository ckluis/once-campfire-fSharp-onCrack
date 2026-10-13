"""Black-box helpers: one app container on a VM-local seed copy, a cookie-keeping HTTP client, a foreign SQLite writer."""
import gzip, http.client, json, os, re, sqlite3, subprocess, time, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGNERS, ALL_TALK = 654632876, 486777696
DAVID, JASON, BOT, KEVIN, JZ, LOU = 127326141, 149087659, 394959859, 712064548, 773523953, 773523958
EMAILS = {DAVID: "david@37signals.com", JASON: "jason@37signals.com", KEVIN: "kevin@37signals.com", JZ: "jz@37signals.com", LOU: "lou@37signals.com"}

class App:
    def __init__(self, name, app, port, seed="default", env=()):
        self.name, self.app, self.port, self.seed, self.env = name, app, port, seed, list(env)
    def __enter__(self):
        out = subprocess.run([f"{HERE}/app.sh", "up", self.name, self.app, str(self.port), self.seed, *self.env], capture_output=True, text=True)
        if out.returncode: raise RuntimeError(out.stdout + out.stderr)
        self.dir = out.stdout.split()[-1]
        self.db_path = f"{self.dir}/db/production.sqlite3"
        return self
    def __exit__(self, *a):
        subprocess.run([f"{HERE}/app.sh", "down", self.name], capture_output=True)
    def db(self):
        c = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        c.execute("PRAGMA busy_timeout=10000")
        return c
    def foreign(self, *stmts):
        c = self.db()
        for s in stmts:
            if isinstance(s, tuple): c.execute(*s)
            else: c.execute(s)
        c.close()
    def logs(self, n=40):
        return subprocess.run(["docker", "logs", "--tail", str(n), f"vfy-{self.name}"], capture_output=True, text=True).stdout

class Resp:
    def __init__(self, status, headers, raw):
        self.status, self.headers, self.raw = status, headers, raw
        enc = self.h("content-encoding")
        self.body = gzip.decompress(raw) if enc == "gzip" and raw else raw
        self.text = self.body.decode("utf-8", "replace")
    def h(self, name):
        for k, v in self.headers:
            if k.lower() == name.lower(): return v
        return None
    def hs(self, name):
        return [v for k, v in self.headers if k.lower() == name.lower()]

class Client:
    def __init__(self, port, host=None):
        self.port = port; self.host = host or f"127.0.0.1:{port}"; self.cookies = {}; self.conn = None; self.extra = {}
    def _c(self):
        if self.conn is None: self.conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        return self.conn
    def cookie_header(self):
        return "; ".join(f"{k}={v}" for k, v in self.cookies.items())
    def req(self, method, path, body=None, headers=None, cookies=True, keep=True):
        h = {"Host": self.host, "Accept": "text/html,application/xhtml+xml", "Accept-Encoding": "gzip", "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
        if cookies and self.cookies: h["Cookie"] = self.cookie_header()
        h.update(self.extra)
        if headers: h.update(headers)
        h = {k: v for k, v in h.items() if v is not None}
        if isinstance(body, dict): body = urllib.parse.urlencode(body); h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        for attempt in range(2):
            try:
                c = self._c(); c.request(method, path, body, h); r = c.getresponse(); raw = r.read(); break
            except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError):
                self.conn = None
                if attempt: raise
        resp = Resp(r.status, r.getheaders(), raw)
        if keep:
            for v in resp.hs("set-cookie"):
                kv = v.split(";")[0]; k, _, val = kv.partition("=")
                if "max-age=0" in v.lower() or "expires=thu, 01 jan 1970" in v.lower(): self.cookies.pop(k, None)
                else: self.cookies[k] = val
        if r.getheader("connection", "").lower() == "close": self.conn = None
        return resp
    def get(self, path, **kw): return self.req("GET", path, **kw)
    def write_headers(self):
        return {"Sec-Fetch-Site": "same-origin", "Origin": f"http://{self.host}"}
    def sign_in(self, email, password="secret123456"):
        page = self.get("/session/new")
        form = {"email_address": email, "password": password}
        m = re.search(r'name="authenticity_token" value="([^"]+)"', page.text)
        if m: form["authenticity_token"] = m.group(1)
        r = self.req("POST", "/session", form, self.write_headers())
        assert r.status in (302, 303), (r.status, r.text[:300])
        return r
    def csrf(self, html):
        m = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
        return m.group(1) if m else None
    def post_message(self, room, text, extra=None, cmid=None):
        page = self.get(f"/rooms/{room}")
        form = {"message[body]": text, "message[client_message_id]": cmid or f"c{time.time_ns()}"}
        tok = self.csrf(page.text)
        if tok: form["authenticity_token"] = tok
        h = self.write_headers(); h["Accept"] = "text/vnd.turbo-stream.html, text/html, application/xhtml+xml"
        if extra: h.update(extra)
        return self.req("POST", f"/rooms/{room}/messages", form, h)

def latest_message(app, room):
    c = app.db(); row = c.execute("select id, creator_id from messages where room_id=? order by created_at desc, id desc limit 1", (room,)).fetchone(); c.close(); return row

def free_disk_ok():
    return True
