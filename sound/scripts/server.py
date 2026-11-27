#!/usr/bin/env python3
# Author: @ayelsew
# https://github.com/ayelsew/linux-for-vivobook-s14
"""server.py: use a phone as a remote measurement microphone for the laptop speakers.

What: a tiny HTTPS server on the laptop. The phone opens its page, taps Start once, and from then on records when
the laptop asks (measure.py) and uploads the recording as a WAV file to logs/phone-mic/.

How: the page asks the browser for the mic with echo cancellation, noise suppression and auto gain OFF (raw audio),
captures it with an AudioWorklet and polls /cmd for record commands. measure.py posts a command, waits until the
phone says it started, plays the test sound on the laptop and waits for the upload.

Why: the laptop's own mics sit next to the speakers and run through DSP. A phone in front of the laptop hears what
a listener hears, and the same setup compares settings (or Linux vs Windows) with numbers instead of memory.

HTTPS is required: phone browsers only allow the mic on secure pages. A self-signed certificate is made on the
first run (the phone shows a warning once). A random token in the URL keeps other devices out.
Port 8443 must be open in the firewall for the local network (see README.md in this folder).

Usage: python3 -I server.py [--port 8443]
"""

import argparse
import http.server
import json
import secrets
import socket
import ssl
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "logs" / "phone-mic"
STATE = {"cmd": None, "started": {}, "done": {}, "seen": 0.0, "settings": None}
LOCK = threading.Lock()

PAGE = r"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Phone mic</title>
<style>
 body{font-family:system-ui,sans-serif;margin:0;padding:24px;background:#1b1b1b;color:#ddd}
 button{font-size:22px;padding:18px 28px;border:0;border-radius:12px;background:#505050;color:#fff;width:100%}
 #st{font-size:20px;margin:20px 0}#info{font-size:13px;color:#999;white-space:pre-wrap}
 #m{height:16px;background:#333;border-radius:8px;overflow:hidden}#b{height:100%;width:0;background:#9c9}
</style></head><body>
<button id="go">Start</button>
<div id="st">Tap Start, then put the phone on a stand in front of the laptop.</div>
<div id="m"><div id="b"></div></div>
<p id="info"></p>
<script>
const T = new URLSearchParams(location.search).get("t");
const st = document.getElementById("st"), info = document.getElementById("info"), bar = document.getElementById("b");
let ctx, rec = null, peak = 0;

const WORKLET = `class Tap extends AudioWorkletProcessor {
  process(inputs) { const c = inputs[0][0]; if (c) this.port.postMessage(c.slice(0)); return true; } }
registerProcessor("tap", Tap);`;

function wav(chunks, rate) {
  const n = chunks.reduce((a, c) => a + c.length, 0);
  const buf = new ArrayBuffer(44 + n * 4), v = new DataView(buf);
  const s = (o, t) => { for (let i = 0; i < t.length; i++) v.setUint8(o + i, t.charCodeAt(i)); };
  s(0, "RIFF"); v.setUint32(4, 36 + n * 4, true); s(8, "WAVE"); s(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 3, true); v.setUint16(22, 1, true);   // float32, mono
  v.setUint32(24, rate, true); v.setUint32(28, rate * 4, true); v.setUint16(32, 4, true); v.setUint16(34, 32, true);
  s(36, "data"); v.setUint32(40, n * 4, true);
  let o = 44; for (const c of chunks) for (const x of c) { v.setFloat32(o, x, true); o += 4; }
  return buf;
}

async function start() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: {
    echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1 } });
  ctx = new AudioContext();
  await ctx.audioWorklet.addModule(URL.createObjectURL(new Blob([WORKLET], { type: "text/javascript" })));
  const node = new AudioWorkletNode(ctx, "tap");
  ctx.createMediaStreamSource(stream).connect(node);
  node.port.onmessage = e => {
    const c = e.data; for (const x of c) peak = Math.max(peak, Math.abs(x));
    if (rec) { rec.chunks.push(c); rec.n += c.length; if (rec.n >= rec.need) finish(); }
  };
  const settings = stream.getAudioTracks()[0].getSettings();
  settings.contextRate = ctx.sampleRate; settings.ua = navigator.userAgent;
  info.textContent = JSON.stringify(settings, null, 1);
  await fetch(`/hello?t=${T}`, { method: "POST", body: JSON.stringify(settings) });
  try { await navigator.wakeLock.request("screen"); } catch (e) {}
  setInterval(() => { bar.style.width = Math.min(100, peak * 100) + "%"; peak *= 0.6; }, 100);
  poll();
}

async function poll() {
  while (true) {
    try {
      const r = await (await fetch(`/cmd?t=${T}`)).json();
      if (r.id && !rec) {
        rec = { id: r.id, chunks: [], n: 0, need: Math.round(r.seconds * ctx.sampleRate) };
        st.textContent = `Recording ${r.seconds} s...`;
        fetch(`/started?t=${T}&id=${r.id}`, { method: "POST" });
      } else if (!rec) st.textContent = "Ready. Waiting for the laptop.";
    } catch (e) { st.textContent = "No connection to the laptop, retrying..."; }
    await new Promise(r => setTimeout(r, 250));
  }
}

async function finish() {
  const r = rec; rec = null; st.textContent = "Uploading...";
  await fetch(`/upload?t=${T}&id=${r.id}`, { method: "POST", body: wav(r.chunks, ctx.sampleRate) });
  st.textContent = "Ready. Waiting for the laptop.";
}

document.getElementById("go").onclick = e => {
  e.target.disabled = true;
  start().catch(err => { st.textContent = "Error: " + err; e.target.disabled = false; });
};
</script></body></html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    token = ""

    def log_message(self, fmt, *args):  # keep the terminal quiet; polling is every 250 ms
        pass

    def reply(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def route(self):
        url = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if q.get("t") != self.token:
            self.reply(403, b"bad token", "text/plain")
            return None, None
        return url.path, q

    def do_GET(self):
        path, q = self.route()
        if path == "/":
            self.reply(200, PAGE.encode(), "text/html; charset=utf-8")
        elif path == "/cmd":  # phone polls
            with LOCK:
                STATE["seen"] = time.time()
                cmd = STATE["cmd"]
            self.reply(200, json.dumps(cmd or {}).encode())
        elif path == "/status":  # laptop asks
            with LOCK:
                i = q.get("id", "")
                s = {"phone_seen_s_ago": round(time.time() - STATE["seen"], 1) if STATE["seen"] else None,
                     "settings": STATE["settings"], "started": STATE["started"].get(i),
                     "file": STATE["done"].get(i)}
            self.reply(200, json.dumps(s).encode())
        elif path is not None:
            self.reply(404, b"", "text/plain")

    def do_POST(self):
        path, q = self.route()
        body = self.rfile.read(int(self.headers.get("Content-Length", 0) or 0))
        if path == "/hello":  # phone reports its mic settings
            with LOCK:
                STATE["settings"] = json.loads(body or b"{}")
            print("phone connected:", json.dumps(STATE["settings"]), flush=True)
            self.reply(200, b"{}")
        elif path == "/record":  # laptop: ask the phone to record
            seconds = float(json.loads(body or b"{}").get("seconds", 5))
            i = secrets.token_hex(4)
            with LOCK:
                STATE["cmd"] = {"id": i, "seconds": seconds}
            self.reply(200, json.dumps({"id": i}).encode())
        elif path == "/started":
            with LOCK:
                STATE["started"][q.get("id", "")] = time.time()
                STATE["cmd"] = None
            self.reply(200, b"{}")
        elif path == "/upload":
            i = q.get("id", "")
            f = DATA / f"{time.strftime('%Y%m%d-%H%M%S')}-{i}.wav"
            f.write_bytes(body)
            with LOCK:
                STATE["done"][i] = str(f)
            print("saved", f, flush=True)
            self.reply(200, b"{}")
        elif path is not None:
            self.reply(404, b"", "text/plain")


def lan_ip():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("192.0.2.1", 9))  # no packet is sent; this only picks the outgoing interface
        return s.getsockname()[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8443)
    args = ap.parse_args()

    DATA.mkdir(parents=True, exist_ok=True)
    ip = lan_ip()
    cert, key = DATA / "cert.pem", DATA / "key.pem"
    if not cert.exists():
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30",
                        "-keyout", str(key), "-out", str(cert), "-subj", "/CN=phone-mic",
                        "-addext", f"subjectAltName=IP:{ip},IP:127.0.0.1"],
                       check=True, capture_output=True)
    Handler.token = secrets.token_urlsafe(9)
    (DATA / "server.json").write_text(json.dumps({"port": args.port, "token": Handler.token}))

    srv = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.load_cert_chain(cert, key)
    srv.socket = tls.wrap_socket(srv.socket, server_side=True)
    print(f"Open on the phone (same Wi-Fi): https://{ip}:{args.port}/?t={Handler.token}", flush=True)
    print("Ctrl+C to stop.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        (DATA / "server.json").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
