#!/usr/bin/env python3
"""Backup, apply direct-VPS override & runtime config, hot-reload Clash Party / Clash Verge
(Windows or macOS), and run end-to-end verification with strict secret/IP redaction.
"""
import argparse
import datetime
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import generate_override_js as gen  # noqa: E402


def redact(s: str) -> str:
    if not s:
        return ""
    def repl(m):
        a, b, c, d = m.groups()
        if a in ("127", "192", "10") or (a == "172" and 16 <= int(b) <= 31):
            return m.group(0)
        return f"{a}.*.*.{d}"
    return re.sub(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b", repl, s)


def get_client_dir(target_os: str, client: str) -> Path:
    home = Path.home()
    if target_os == "windows":
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    else:
        base = home / "Library" / "Application Support"
    if client == "clash-party":
        return base / "mihomo-party"
    return base / "io.github.clash-verge-rev.clash-verge-rev"


def detect_local_ssh_tunnel() -> bool:
    s = socket.socket()
    s.settimeout(0.5)
    try:
        return s.connect_ex(("127.0.0.1", 17942)) == 0
    finally:
        s.close()


def find_control_endpoint(target_os: str, client: str):
    if target_os == "windows":
        try:
            pipes = os.listdir(r"\\.\pipe\\")
        except Exception:
            pipes = []
        if client == "clash-party":
            for p in pipes:
                if p.lower().startswith(r"mihomoparty\mihomo"):
                    return ("pipe", r"\\.\pipe\\" + p)
        else:
            for p in pipes:
                if p.lower() == "verge-mihomo" or p.lower().startswith("verge-mihomo-"):
                    return ("pipe", r"\\.\pipe\\" + p)
    else:
        cands = ["/tmp/mihomo-party.sock"] if client == "clash-party" else ["/tmp/verge/verge-mihomo.sock"]
        for c in cands:
            if os.path.exists(c):
                return ("unix", c)
    return (None, None)


def mihomo_req(endpoint, method: str, path: str, body=None):
    kind, addr = endpoint
    if not kind:
        return None, ""
    payload = json.dumps(body).encode("utf-8") if body is not None else b""
    hdr = (
        f"{method} {path} HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n"
    ).encode("utf-8")
    if kind == "pipe":
        with open(addr, "r+b", buffering=0) as f:
            f.write(hdr + payload)
            chunks = []
            while True:
                try:
                    d = f.read(65536)
                    if not d:
                        break
                    chunks.append(d)
                except OSError:
                    break
        raw = b"".join(chunks)
    else:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(8)
        s.connect(addr)
        s.sendall(hdr + payload)
        chunks = []
        while True:
            d = s.recv(65536)
            if not d:
                break
            chunks.append(d)
        s.close()
        raw = b"".join(chunks)

    hdr_raw, body_raw = raw.split(b"\r\n\r\n", 1) if b"\r\n\r\n" in raw else (raw, b"")
    st = hdr_raw.decode("utf-8", errors="ignore").splitlines()[0] if hdr_raw else ""
    if b"transfer-encoding: chunked" in hdr_raw.lower():
        decoded = bytearray()
        i = 0
        while i < len(body_raw):
            j = body_raw.find(b"\r\n", i)
            if j == -1:
                break
            sz = int(body_raw[i:j].split(b";", 1)[0].strip() or b"0", 16)
            if sz == 0:
                break
            i = j + 2
            decoded.extend(body_raw[i:i + sz])
            i += sz + 2
        body_raw = bytes(decoded)
    return st, body_raw.decode("utf-8", errors="ignore").strip()


def ensure_party_override_registered(party_dir: Path, script_id: str, display_name: str):
    ov_yaml = party_dir / "override.yaml"
    now_ms = int(time.time() * 1000)
    if not ov_yaml.is_file():
        ov_yaml.write_text(
            f"items:\n  - id: {script_id}\n    name: {display_name}\n    type: local\n    ext: js\n    global: true\n    updated: {now_ms}\n",
            encoding="utf-8"
        )
        return
    txt = ov_yaml.read_text(encoding="utf-8", errors="ignore")
    if f"id: {script_id}" in txt or f'id: "{script_id}"' in txt:
        return
    if re.search(r"items:\s*\[", txt):
        entry = (
            f"    {{\n"
            f"      id: {script_id},\n"
            f"      name: {display_name},\n"
            f"      type: local,\n"
            f"      ext: js,\n"
            f"      global: true,\n"
            f"      updated: {now_ms}\n"
            f"    }}"
        )
        if re.search(r"items:\s*\[\s*\]", txt):
            txt = re.sub(r"items:\s*\[\s*\]", f"items:\n  [\n{entry}\n  ]", txt, count=1)
        else:
            idx = txt.rfind("]")
            if idx != -1:
                txt = txt[:idx].rstrip() + ",\n" + entry + "\n  ]\n"
    else:
        txt = txt.rstrip() + (
            f"\n  - id: {script_id}\n"
            f"    name: {display_name}\n"
            f"    type: local\n"
            f"    ext: js\n"
            f"    global: true\n"
            f"    updated: {now_ms}\n"
        )
    ov_yaml.write_text(txt, encoding="utf-8")


def patch_runtime_yaml(yaml_path: Path, creds: dict, target_os: str, use_tailscale: bool, use_ssh: bool):
    proxies, group = gen.build_proxies_and_group(creds, use_tailscale, use_ssh)
    ytxt = yaml_path.read_text(encoding="utf-8", errors="ignore")

    ytxt = re.sub(r'^\s*- \{"name":"Antigravity-VPS(?:-[A-Za-z0-9]+)?",[^\n]+\}\r?\n', '', ytxt, flags=re.M)
    ytxt = re.sub(r'^  - name: Antigravity-VPS(?:-[A-Za-z0-9]+)?\r?\n(?:    .*\r?\n)+', '', ytxt, flags=re.M)
    ytxt = re.sub(r'^- name: Antigravity-VPS(?:-[A-Za-z0-9]+)?\r?\n(?:  .*\r?\n)+', '', ytxt, flags=re.M)

    m_px = re.search(r"^proxies:\r?\n([ \t]*)- ", ytxt, re.M)
    px_indent = m_px.group(1) if m_px else "  "
    proxy_lines = "".join(f"{px_indent}- {json.dumps(p, ensure_ascii=False)}\n" for p in proxies)
    if re.search(r"^proxies:\r?\n", ytxt, re.M):
        ytxt = re.sub(r"^proxies:\r?\n", "proxies:\n" + proxy_lines, ytxt, count=1, flags=re.M)
    else:
        ytxt = "proxies:\n" + proxy_lines + ytxt

    m_pg = re.search(r"^proxy-groups:\r?\n([ \t]*)- ", ytxt, re.M)
    pg_indent = m_pg.group(1) if m_pg else "  "
    group_line = f"{pg_indent}- {json.dumps(group, ensure_ascii=False)}\n"
    if re.search(r"^proxy-groups:\r?\n", ytxt, re.M):
        ytxt = re.sub(r"^proxy-groups:\r?\n", "proxy-groups:\n" + group_line, ytxt, count=1, flags=re.M)
    else:
        ytxt = "proxy-groups:\n" + group_line + ytxt

    ag_listener_line = '- {"name":"antigravity-app-only","type":"mixed","listen":"127.0.0.1","port":17941,"proxy":"Antigravity-VPS"}\n'
    if "antigravity-app-only" not in ytxt:
        if re.search(r"^listeners:\r?\n", ytxt, re.M):
            ytxt = re.sub(r"^listeners:\r?\n", "listeners:\n" + ag_listener_line, ytxt, count=1, flags=re.M)
        else:
            ytxt = re.sub(r"^proxies:\r?\n", "listeners:\n" + ag_listener_line + "proxies:\n", ytxt, count=1, flags=re.M)

    proc_rules = gen.WINDOWS_PROCESS_RULES if target_os == "windows" else gen.MACOS_PROCESS_RULES
    direct_top = gen.build_direct_rules(creds)
    vps_rules = [f"{k},Antigravity-VPS" for k in (proc_rules + gen.VPS_DOMAIN_KEYS)]
    top_all = direct_top + vps_rules
    drop_keys = set(",".join(r.split(",")[:2]) for r in top_all)

    m_rules = re.search(r"^rules:\r?\n", ytxt, re.M)
    if m_rules:
        before = ytxt[:m_rules.end()]
        after = ytxt[m_rules.end():]
        m_next = re.search(r"^[a-zA-Z0-9_-]+:", after, re.M)
        rblock = after[:m_next.start()] if m_next else after
        tail = after[m_next.start():] if m_next else ""

        m_ri = re.search(r"^([ \t]*)- ", rblock, re.M)
        r_indent = m_ri.group(1) if m_ri else "  "
        kept = []
        for line in rblock.splitlines():
            s = line.strip()
            if not s.startswith("- "):
                continue
            raw_r = s[2:].strip()
            unq = raw_r.strip('"').strip("'")
            parts = unq.split(",")
            if len(parts) >= 2 and ",".join(parts[:2]) in drop_keys:
                continue
            if parts and parts[-1] == "Antigravity-VPS":
                continue
            kept.append(raw_r)

        def fmt_rule(r):
            return json.dumps(r, ensure_ascii=False) if ("\\" in r or "*" in r) else r

        new_rules = [f"{r_indent}- {fmt_rule(r)}" for r in top_all] + [f"{r_indent}- {r}" for r in kept]
        ytxt = before + "\n".join(new_rules) + "\n" + tail

    yaml_path.write_text(ytxt, encoding="utf-8")


def run_curl(url: str, proxy: str, timeout: int = 10) -> str:
    curl_bin = "curl.exe" if platform.system() == "Windows" else "curl"
    cmd = [
        curl_bin, "-sS", "-o", os.devnull, "--max-time", str(timeout),
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "-w", "HTTP=%{http_code} tls=%{time_appconnect}s ttfb=%{time_starttransfer}s total=%{time_total}s",
    ]
    if platform.system() == "Windows":
        cmd.append("--ssl-no-revoke")
    if proxy:
        cmd.extend(["-x", proxy])
    cmd.append(url)
    p = subprocess.run(cmd, capture_output=True, text=True, errors="ignore", timeout=timeout + 5)
    return p.stdout.strip() if p.returncode == 0 else f"ERR({p.returncode}): {redact(p.stderr.strip().splitlines()[-1] if p.stderr.strip() else 'failed')}"


def verify_all(target_os: str, client: str, creds: dict, use_tailscale: bool, proxy_port: int):
    print("\n=== END-TO-END VERIFICATION ===")
    ep = find_control_endpoint(target_os, client)
    if ep[0]:
        _, gbody = mihomo_req(ep, "GET", "/proxies/Antigravity-VPS")
        try:
            gd = json.loads(gbody)
            print(f"  [LIVE GROUP] Antigravity-VPS -> now={gd.get('now')} all={gd.get('all')}")
        except Exception:
            print("  [LIVE GROUP] Unable to parse group state")
        for node in ["Antigravity-VPS-Reality", "Antigravity-VPS-Hy2", "Antigravity-VPS-TS"]:
            _, d = mihomo_req(ep, "GET", f"/proxies/{node}/delay?timeout=5000&url=https://www.gstatic.com/generate_204")
            if d:
                print(f"  [NODE DELAY] {node:<24}: {d}")
    else:
        print("  [INFO] Live control socket/pipe not found; skipping API delay query (reload client UI to activate).")

    px = f"http://127.0.0.1:{proxy_port}"
    print(f"\n  Testing via local proxy {px}:")
    checks = [
        ("api.openai.com", "https://api.openai.com/v1/models"),
        ("codex responses", "https://chatgpt.com/backend-api/codex/responses"),
        ("grok.com", "https://grok.com/"),
        ("gemini.google.com", "https://gemini.google.com/"),
        ("challenges.cf", "https://challenges.cloudflare.com/"),
    ]
    if creds.get("direct_check_url"):
        checks.append(("private DIRECT check", creds["direct_check_url"]))
    for label, url in checks:
        print(f"    {label:<20}: {run_curl(url, px, 10)}")

    if use_tailscale and creds.get("la_ts_ip") and not str(creds.get("la_ts_ip")).startswith("<"):
        vps_node = creds.get("tailscale_vps_node", "la-vps")
        print(f"\n  Testing Tailscale fallback ({vps_node}:{creds.get('la_ts_port', 17942)}):")
        ts_bin = shutil.which("tailscale") or (
            "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
            if os.path.exists("/Applications/Tailscale.app/Contents/MacOS/Tailscale") else "tailscale"
        )
        tp = subprocess.run([ts_bin, "ping", "-c", "2", vps_node], capture_output=True, text=True, errors="ignore", timeout=10)
        print("    tailscale ping :", redact(tp.stdout.strip().splitlines()[-1] if tp.stdout.strip() else tp.stderr.strip()))
        ts_px = f"socks5h://{creds['la_ts_ip']}:{creds.get('la_ts_port', 17942)}"
        print(f"    socks5 openai  : {run_curl('https://api.openai.com/v1/models', ts_px, 10)}")


def main():
    ap = argparse.ArgumentParser(description="Apply direct-VPS client config and verify.")
    ap.add_argument("--os", dest="target_os", choices=["windows", "macos"],
                    default="windows" if platform.system() == "Windows" else "macos")
    ap.add_argument("--client", required=True, choices=["clash-party", "clash-verge"])
    ap.add_argument("--creds", type=Path, default=Path.home() / ".config" / "la-vps-proxy" / "vps-creds.json")
    ap.add_argument("--tailscale", choices=["on", "off"], default="on")
    ap.add_argument("--ssh-fallback", choices=["auto", "on", "off"], default="auto")
    ap.add_argument("--non-ai-target", default="", help="Optional node/group name for non-AI custom rules.")
    ap.add_argument("--proxy-port", type=int, default=0, help="Override proxy port for verification (default: 7890 party / 7897 verge)")
    ap.add_argument("--verify-only", action="store_true")
    args = ap.parse_args()

    if not args.creds.is_file():
        print(f"ERROR: Credentials file not found: {args.creds}", file=sys.stderr)
        sys.exit(1)
    creds = json.loads(args.creds.read_text(encoding="utf-8"))
    use_ts = (args.tailscale == "on")
    use_ssh = detect_local_ssh_tunnel() if args.ssh_fallback == "auto" else (args.ssh_fallback == "on")
    proxy_port = args.proxy_port or (7890 if args.client == "clash-party" else 7897)

    if args.verify_only:
        verify_all(args.target_os, args.client, creds, use_ts, proxy_port)
        return

    cdir = get_client_dir(args.target_os, args.client)
    if not cdir.is_dir():
        print(f"ERROR: Client directory not found: {cdir}. Install/launch {args.client} once first.", file=sys.stderr)
        sys.exit(1)

    ts_tag = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bk_dir = cdir / "backups" / f"la-vps-onboarding-{ts_tag}"
    bk_dir.mkdir(parents=True, exist_ok=True)

    js_content = gen.generate_js(
        creds, args.target_os, args.client, use_ts, use_ssh,
        enable_listener=True, non_ai_target_override=args.non_ai_target
    )

    if args.client == "clash-party":
        ov_dir = cdir / "override"
        ov_dir.mkdir(parents=True, exist_ok=True)
        ov_yaml = cdir / "override.yaml"
        script_id = "la-vps-ai-routing"
        js_path = ov_dir / f"{script_id}.js"
        if js_path.is_file():
            shutil.copy2(js_path, bk_dir / js_path.name)
        if ov_yaml.is_file():
            shutil.copy2(ov_yaml, bk_dir / "override.yaml")
        js_path.write_text(js_content, encoding="utf-8")
        ensure_party_override_registered(cdir, script_id, "VPS AI Routing (Reality+Hy2+TS)")
        print(f"[APPLY] Updated Clash Party override: {js_path}")
        runtime_yaml = cdir / "work" / "config.yaml"
    else:
        js_path = cdir / "profiles" / "Script.js"
        js_path.parent.mkdir(parents=True, exist_ok=True)
        if js_path.is_file():
            shutil.copy2(js_path, bk_dir / "Script.js")
        js_path.write_text(js_content, encoding="utf-8")
        print(f"[APPLY] Updated Clash Verge override: {js_path}")
        runtime_yaml = cdir / "clash-verge.yaml"

    if runtime_yaml.is_file():
        shutil.copy2(runtime_yaml, bk_dir / runtime_yaml.name)
        patch_runtime_yaml(runtime_yaml, creds, args.target_os, use_ts, use_ssh)
        print(f"[APPLY] Patched runtime config: {runtime_yaml} (backup in {bk_dir})")
        ep = find_control_endpoint(args.target_os, args.client)
        if ep[0]:
            st, _ = mihomo_req(ep, "PUT", "/configs?force=true", {"path": str(runtime_yaml)})
            print(f"[RELOAD] Hot-reload response: {st}")
            time.sleep(1.5)
        else:
            print("[RELOAD] Client core pipe/socket not active; open/reload client UI to activate.")
    else:
        print(f"[INFO] Runtime YAML not present yet ({runtime_yaml}); override JS will take effect once profile is loaded.")

    verify_all(args.target_os, args.client, creds, use_ts, proxy_port)


if __name__ == "__main__":
    main()
