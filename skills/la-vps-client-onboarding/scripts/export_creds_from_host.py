#!/usr/bin/env python3
"""Safely extract direct-VPS client credentials into ~/.config/la-vps-proxy/vps-creds.json
without printing any raw IP, UUID, key, or password to stdout/stderr.
"""
import argparse
import json
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def default_creds_path() -> Path:
    return Path.home() / ".config" / "la-vps-proxy" / "vps-creds.json"


def harden_permissions(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if platform.system() == "Windows":
        try:
            principal = subprocess.check_output(["whoami"], text=True, stderr=subprocess.DEVNULL).strip()
        except Exception:
            dom = os.environ.get("USERDOMAIN", "")
            usr = os.environ.get("USERNAME", "")
            principal = f"{dom}\\{usr}" if dom and usr else usr
        if principal:
            subprocess.run(
                ["icacls", str(path.parent), "/inheritance:r", "/grant:r", f"{principal}:(OI)(CI)F", "SYSTEM:(OI)(CI)F"],
                capture_output=True, text=True, check=False
            )
            subprocess.run(
                ["icacls", str(path), "/inheritance:r", "/grant:r", f"{principal}:F", "SYSTEM:F"],
                capture_output=True, text=True, check=False
            )
    else:
        os.chmod(path.parent, stat.S_IRWXU)
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def extract_from_js(js_path: Path):
    txt = js_path.read_text(encoding="utf-8", errors="ignore")
    m_r = re.search(r"const\s+ag(?:Vps)?Reality\s*=\s*(\{.*?\});", txt)
    m_h = re.search(r"const\s+ag(?:Vps)?Hy2\s*=\s*(\{.*?\});", txt)
    m_t = re.search(r"const\s+ag(?:Vps)?Ts\s*=\s*(\{.*?\});", txt)
    if not (m_r and m_h):
        return None
    r = json.loads(m_r.group(1))
    h = json.loads(m_h.group(1))
    t = json.loads(m_t.group(1)) if m_t else {}
    return {
        "la_pub_ip": r["server"],
        "la_ts_ip": t.get("server", ""),
        "la_ts_port": int(t.get("port", 17942)),
        "tailscale_vps_node": "la-vps",
        "direct_domains": [],
        "direct_check_url": "",
        "non_ai_target": "",
        "reality": {
            "port": int(r.get("port", 443)),
            "uuid": r["uuid"],
            "flow": r.get("flow", "xtls-rprx-vision"),
            "servername": r.get("servername", "www.apple.com"),
            "public_key": r["reality-opts"]["public-key"],
            "short_id": r["reality-opts"]["short-id"],
            "fingerprint": r.get("client-fingerprint", "chrome"),
        },
        "hysteria2": {
            "port": int(h.get("port", 443)),
            "password": h["password"],
            "sni": h.get("sni", "bing.com"),
            "skip_cert_verify": bool(h.get("skip-cert-verify", True)),
            "up": h.get("up", "30 Mbps"),
            "down": h.get("down", "100 Mbps"),
        },
    }


def find_local_candidates():
    home = Path.home()
    if platform.system() == "Windows":
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    else:
        base = home / "Library" / "Application Support"
    cands = [
        base / "mihomo-party" / "override" / "la-vps-ai-routing.js",
        base / "io.github.clash-verge-rev.clash-verge-rev" / "profiles" / "Script.js",
    ]
    ov_dir = base / "mihomo-party" / "override"
    if ov_dir.is_dir():
        for p in sorted(ov_dir.glob("*.js")):
            if p not in cands:
                cands.append(p)
    return cands


def detect_tailscale_vps_ip(node_name: str = "la-vps") -> str:
    ts_bin = shutil.which("tailscale") or (
        "/Applications/Tailscale.app/Contents/MacOS/Tailscale"
        if os.path.exists("/Applications/Tailscale.app/Contents/MacOS/Tailscale") else "tailscale"
    )
    try:
        out = subprocess.check_output([ts_bin, "status"], text=True, stderr=subprocess.DEVNULL, timeout=5)
        for line in out.splitlines():
            if node_name in line:
                return line.split()[0]
    except Exception:
        pass
    return ""


def main():
    ap = argparse.ArgumentParser(description="Export direct-VPS credentials safely to private JSON file.")
    ap.add_argument("--from-local", action="store_true", help="Extract from local Clash Party / Clash Verge override script.")
    ap.add_argument("--from-js", type=Path, help="Extract from a specific override .js file.")
    ap.add_argument("--vps-node", default="la-vps", help="Tailscale node name for the overseas VPS.")
    ap.add_argument("--output", type=Path, default=default_creds_path(), help="Output private JSON path.")
    args = ap.parse_args()

    creds = None
    source_used = None
    if args.from_js:
        creds = extract_from_js(args.from_js)
        source_used = str(args.from_js)
    else:
        for cand in find_local_candidates():
            if cand.is_file():
                creds = extract_from_js(cand)
                if creds:
                    source_used = str(cand)
                    break

    if not creds:
        print("ERROR: Could not extract Reality/Hysteria2 credentials from local config.", file=sys.stderr)
        sys.exit(1)

    creds["tailscale_vps_node"] = args.vps_node
    if not creds.get("la_ts_ip"):
        creds["la_ts_ip"] = detect_tailscale_vps_ip(args.vps_node)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(creds, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    harden_permissions(args.output)
    print(f"OK: Exported credentials from {source_used}")
    print(f"    Saved to: {args.output} (permissions hardened; secrets omitted from output)")
    print(f"    Fields: reality=yes (port {creds['reality']['port']}, sni={creds['reality']['servername']}), "
          f"hysteria2=yes (port {creds['hysteria2']['port']}), tailscale={'yes' if creds.get('la_ts_ip') else 'no'}")


if __name__ == "__main__":
    main()
