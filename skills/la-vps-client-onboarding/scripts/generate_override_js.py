#!/usr/bin/env python3
"""Generate cross-platform (Windows / macOS) Clash Party or Clash Verge override JS
for a direct overseas VPS (VLESS-Reality TCP 443 -> Hysteria2 UDP 443 -> Tailscale fallback).
Reads credentials strictly from a local private JSON file; never prints raw secrets or IPs.
"""
import argparse
import json
import sys
from pathlib import Path

WINDOWS_PROCESS_RULES = [
    r"PROCESS-PATH-WILDCARD,C:\Users\*\AppData\Local\Programs\antigravity\*",
    "PROCESS-NAME,Antigravity.exe",
    "PROCESS-NAME,language_server.exe",
]

MACOS_PROCESS_RULES = [
    "PROCESS-PATH-WILDCARD,/Applications/Antigravity.app/*",
    "PROCESS-NAME,Antigravity",
    "PROCESS-NAME,language_server_macos_arm64",
    "PROCESS-NAME,language_server_macos_x64",
]

VPS_DOMAIN_KEYS = [
    # Antigravity & Gemini / Google AI / Auth
    "DOMAIN-SUFFIX,antigravity.google",
    "DOMAIN-SUFFIX,antigravity.google.com",
    "DOMAIN-SUFFIX,antigravity-unleash.goog",
    "DOMAIN-SUFFIX,gemini.google.com",
    "DOMAIN-SUFFIX,gemini.google",
    "DOMAIN-SUFFIX,bard.google.com",
    "DOMAIN-SUFFIX,ai.google.dev",
    "DOMAIN-SUFFIX,generativeai.google",
    "DOMAIN-SUFFIX,aistudio.google.com",
    "DOMAIN-SUFFIX,makersuite.google.com",
    "DOMAIN-SUFFIX,generativelanguage.googleapis.com",
    "DOMAIN-SUFFIX,cloudcode-pa.googleapis.com",
    "DOMAIN-SUFFIX,daily-cloudcode-pa.googleapis.com",
    "DOMAIN-SUFFIX,daily-cloudcode-pa.sandbox.googleapis.com",
    "DOMAIN-SUFFIX,geminiweb-pa.clients6.google.com",
    "DOMAIN-SUFFIX,geminiweb-pa.clients.google.com",
    "DOMAIN-SUFFIX,gemini.gstatic.com",
    "DOMAIN-SUFFIX,appsgenaiserver-pa.clients6.google.com",
    "DOMAIN-SUFFIX,appsgenaiserver-pa.googleapis.com",
    "DOMAIN-SUFFIX,alkalimakersuite-pa.clients6.google.com",
    "DOMAIN-SUFFIX,alkali-pa.clients6.google.com",
    "DOMAIN-SUFFIX,alkalicore-pa.clients6.google.com",
    "DOMAIN-SUFFIX,robinfrontend-pa.clients6.google.com",
    "DOMAIN-SUFFIX,robinfrontend-pa.googleapis.com",
    "DOMAIN-SUFFIX,aisandbox-pa.clients6.google.com",
    "DOMAIN-SUFFIX,aisandbox-pa.googleapis.com",
    "DOMAIN-SUFFIX,proactivebackend-pa.googleapis.com",
    "DOMAIN-SUFFIX,waa-pa.clients6.google.com",
    "DOMAIN-SUFFIX,cloudaicompanion.googleapis.com",
    "DOMAIN-SUFFIX,notebooklm.google",
    "DOMAIN-SUFFIX,notebooklm.google.com",
    "DOMAIN-SUFFIX,jules.google.com",
    "DOMAIN-SUFFIX,labs.google",
    "DOMAIN-SUFFIX,deepmind.com",
    "DOMAIN-SUFFIX,deepmind.google",
    "DOMAIN,aiplatform.googleapis.com",
    "DOMAIN,aida.googleapis.com",
    "DOMAIN,www.googleapis.com",
    "DOMAIN-SUFFIX,accounts.google.com",
    "DOMAIN-SUFFIX,oauth2.googleapis.com",
    # Claude / Anthropic
    "DOMAIN-SUFFIX,clau.de",
    "DOMAIN-SUFFIX,claude.ai",
    "DOMAIN-SUFFIX,claude.com",
    "DOMAIN-SUFFIX,claude.app",
    "DOMAIN-SUFFIX,anthropic.com",
    "DOMAIN-SUFFIX,claudeusercontent.com",
    "DOMAIN-SUFFIX,claudemcpcontent.com",
    "DOMAIN-SUFFIX,modelcontextprotocol.io",
    # OpenAI / ChatGPT / Codex
    "DOMAIN-KEYWORD,openai",
    "DOMAIN-SUFFIX,openai.com",
    "DOMAIN-SUFFIX,chatgpt.com",
    "DOMAIN-SUFFIX,chatgpt.site",
    "DOMAIN-SUFFIX,chatgpt-team.site",
    "DOMAIN-SUFFIX,chatgpt.livekit.cloud",
    "DOMAIN-SUFFIX,oaistatic.com",
    "DOMAIN-SUFFIX,oaiusercontent.com",
    "DOMAIN-SUFFIX,oaistatsig.com",
    "DOMAIN-SUFFIX,sora.com",
    "DOMAIN-SUFFIX,openaiapi-site.azureedge.net",
    "DOMAIN-SUFFIX,openaicom.imgix.net",
    "DOMAIN,openaicomproductionae4b.blob.core.windows.net",
    "DOMAIN,chat.openai.com.cdn.cloudflare.net",
    "DOMAIN,openai-api.arkoselabs.com",
    "DOMAIN,openaicom-api-bdcpf8c6d2e9atf6.z01.azurefd.net",
    "DOMAIN,production-openaicom-storage.azureedge.net",
    "DOMAIN-SUFFIX,ai.com",
    # Grok / xAI
    "DOMAIN-SUFFIX,grok.com",
    "DOMAIN-SUFFIX,x.ai",
    "DOMAIN-SUFFIX,grokusercontent.com",
    "DOMAIN-SUFFIX,grok.x.com",
    "DOMAIN-SUFFIX,accounts.x.ai",
    "DOMAIN,accounts.spacex.ai",
    # Meta / Muse
    "DOMAIN-SUFFIX,muse.ai",
    "DOMAIN-SUFFIX,muse.meta.com",
    "DOMAIN-SUFFIX,meta.ai",
    "DOMAIN-SUFFIX,auth.meta.com",
    "DOMAIN-SUFFIX,metaaiusercontent.com",
    "DOMAIN-SUFFIX,ecto1usercontent.com",
    "DOMAIN-SUFFIX,meta-agents-apps.workers.dev",
    "DOMAIN-SUFFIX,llama.com",
    # Other AI & companion challenges/auth
    "DOMAIN-SUFFIX,perplexity.ai",
    "DOMAIN-SUFFIX,pplx.ai",
    "DOMAIN-SUFFIX,openrouter.ai",
    "DOMAIN-SUFFIX,cursor.com",
    "DOMAIN-SUFFIX,cursor.sh",
    "DOMAIN-SUFFIX,cursorapi.com",
    "DOMAIN-SUFFIX,codeium.com",
    "DOMAIN-SUFFIX,windsurf.com",
    "DOMAIN-SUFFIX,mistral.ai",
    "DOMAIN-SUFFIX,poe.com",
    "DOMAIN-SUFFIX,cohere.com",
    "DOMAIN-SUFFIX,elevenlabs.io",
    "DOMAIN-SUFFIX,client-api.arkoselabs.com",
    "DOMAIN-SUFFIX,challenges.cloudflare.com",
    "DOMAIN-SUFFIX,statsigapi.net",
    "DOMAIN-SUFFIX,featuregates.org",
    "DOMAIN-SUFFIX,identrust.com",
    "DOMAIN-SUFFIX,intercom.io",
    "DOMAIN-SUFFIX,intercomcdn.com",
]

NON_AI_CUSTOM_KEYS = [
    "DOMAIN-SUFFIX,paypal.com",
    "DOMAIN-SUFFIX,paypalobjects.com",
    "DOMAIN-SUFFIX,ping0.cc",
    "GEOSITE,google",
    "DOMAIN-SUFFIX,recaptcha.net",
    "DOMAIN,accounts.google.cn",
]


def build_direct_rules(creds: dict):
    rules = []
    for dom in (creds.get("direct_domains") or []):
        d = str(dom).strip().lstrip(".")
        if d and not d.startswith("<"):
            rules.append(f"DOMAIN-SUFFIX,{d},DIRECT")
    rules.extend([
        "IP-CIDR,127.0.0.0/8,DIRECT,no-resolve",
        "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
        "IP-CIDR6,::1/128,DIRECT,no-resolve",
    ])
    return rules


def build_proxies_and_group(creds: dict, use_tailscale: bool, use_ssh: bool):
    r = creds["reality"]
    h = creds["hysteria2"]
    proxies = [
        {
            "name": "Antigravity-VPS-Reality",
            "type": "vless",
            "server": creds["la_pub_ip"],
            "port": int(r.get("port", 443)),
            "uuid": r["uuid"],
            "network": "tcp",
            "tls": True,
            "udp": True,
            "flow": r.get("flow", "xtls-rprx-vision"),
            "servername": r.get("servername", "www.apple.com"),
            "client-fingerprint": r.get("fingerprint", "chrome"),
            "reality-opts": {
                "public-key": r["public_key"],
                "short-id": r["short_id"],
            },
        },
        {
            "name": "Antigravity-VPS-Hy2",
            "type": "hysteria2",
            "server": creds["la_pub_ip"],
            "port": int(h.get("port", 443)),
            "password": h["password"],
            "sni": h.get("sni", "bing.com"),
            "skip-cert-verify": bool(h.get("skip_cert_verify", True)),
            "up": h.get("up", "30 Mbps"),
            "down": h.get("down", "100 Mbps"),
        },
    ]
    group_members = ["Antigravity-VPS-Reality", "Antigravity-VPS-Hy2"]

    if use_tailscale and creds.get("la_ts_ip") and not str(creds.get("la_ts_ip")).startswith("<"):
        proxies.append({
            "name": "Antigravity-VPS-TS",
            "type": "socks5",
            "server": creds["la_ts_ip"],
            "port": int(creds.get("la_ts_port", 17942)),
            "udp": False,
        })
        group_members.append("Antigravity-VPS-TS")

    if use_ssh:
        proxies.append({
            "name": "Antigravity-VPS-SSH",
            "type": "socks5",
            "server": "127.0.0.1",
            "port": 17942,
            "udp": False,
        })
        group_members.append("Antigravity-VPS-SSH")

    group = {
        "name": "Antigravity-VPS",
        "type": "fallback",
        "proxies": group_members,
        "url": "https://www.gstatic.com/generate_204",
        "interval": 120,
    }
    return proxies, group


def generate_js(
    creds: dict,
    target_os: str,
    client: str,
    use_tailscale: bool,
    use_ssh: bool,
    enable_listener: bool,
    non_ai_target_override: str = "",
) -> str:
    proxies, group = build_proxies_and_group(creds, use_tailscale, use_ssh)
    proc_rules = WINDOWS_PROCESS_RULES if target_os == "windows" else MACOS_PROCESS_RULES
    vps_keys = proc_rules + VPS_DOMAIN_KEYS
    direct_rules = build_direct_rules(creds)

    fn_sig = "function main(config, profileName)" if client == "clash-verge" else "function main(config)"
    proxy_decls = []
    proxy_var_names = []
    for p in proxies:
        vname = "agVps" + p["name"].replace("Antigravity-VPS-", "")
        proxy_decls.append(f"  const {vname} = {json.dumps(p, ensure_ascii=False)};")
        proxy_var_names.append(vname)

    listener_block = ""
    if enable_listener:
        listener_block = """
  const agListener = {"name": "antigravity-app-only", "type": "mixed", "listen": "127.0.0.1", "port": 17941, "proxy": "Antigravity-VPS"};
  const rawListeners = Array.isArray(config.listeners) ? config.listeners : [];
  config.listeners = [
    agListener,
    ...rawListeners.filter(l => l && l.name !== agListener.name)
  ];"""

    preferred = non_ai_target_override or creds.get("non_ai_target") or ""
    fallback_candidates = [c for c in [preferred, "♻️ 自动选择 - US", "🔰 节点选择", "Proxy", "PROXY", "Auto", "Fallback"] if c]
    chain_desc = " -> ".join(group["proxies"])

    js = f"""// Direct-VPS unified AI routing ({client} / {target_os}):
// - AI models + companion auth/challenges -> Antigravity-VPS ({chain_desc})
// - Private direct domains & Tailscale 100.64.0.0/10 -> DIRECT
// - Non-AI custom rules -> preferred subscription node/group (if present)
{fn_sig} {{
{chr(10).join(proxy_decls)}
  const agVpsGroup = {json.dumps(group, ensure_ascii=False)};

  const managedNames = new Set([
    "Antigravity-VPS",
    "Antigravity-VPS-Reality",
    "Antigravity-VPS-Hy2",
    "Antigravity-VPS-TS",
    "Antigravity-VPS-SSH"
  ]);
  const rawProxies = Array.isArray(config.proxies) ? config.proxies : [];
  config.proxies = [
    {", ".join(proxy_var_names)},
    ...rawProxies.filter(p => p && !managedNames.has(p.name))
  ];

  const rawGroups = Array.isArray(config["proxy-groups"]) ? config["proxy-groups"] : [];
  config["proxy-groups"] = [
    agVpsGroup,
    ...rawGroups.filter(g => g && g.name !== "Antigravity-VPS")
  ];{listener_block}

  const fallbackCandidates = {json.dumps(fallback_candidates, ensure_ascii=False)};
  const existingNames = new Set([
    ...config.proxies.map(p => p && p.name),
    ...config["proxy-groups"].map(g => g && g.name)
  ]);
  const nonAiTarget = fallbackCandidates.find(n => existingNames.has(n)) || "Antigravity-VPS";

  const directRules = {json.dumps(direct_rules, indent=4, ensure_ascii=False)};
  const vpsModelKeys = {json.dumps(vps_keys, indent=4, ensure_ascii=False)};
  const nonAiCustomKeys = {json.dumps(NON_AI_CUSTOM_KEYS, indent=4, ensure_ascii=False)};

  const rules = [
    ...directRules,
    ...vpsModelKeys.map(k => k + ",Antigravity-VPS"),
    ...nonAiCustomKeys.map(k => k + "," + nonAiTarget)
  ];

  const routeKeys = new Set(rules.map(r => r.split(",").slice(0, 2).join(",")));
  const oldTargets = new Set(["Antigravity-VPS"]);

  config.rules = [
    ...rules,
    ...(Array.isArray(config.rules) ? config.rules : []).filter(r => {{
      if (typeof r !== "string") return false;
      const parts = r.split(",");
      const key = parts.slice(0, 2).join(",");
      const target = parts[parts.length - 1];
      if (rules.includes(r) || routeKeys.has(key) || oldTargets.has(target)) return false;
      if (/^DOMAIN-KEYWORD,openai,/i.test(r)) return false;
      return true;
    }})
  ];

  return config;
}}
"""
    return js


def main():
    ap = argparse.ArgumentParser(description="Generate direct-VPS override JS for Clash Party or Clash Verge.")
    ap.add_argument("--os", dest="target_os", required=True, choices=["windows", "macos"])
    ap.add_argument("--client", required=True, choices=["clash-party", "clash-verge"])
    ap.add_argument("--creds", type=Path, default=Path.home() / ".config" / "la-vps-proxy" / "vps-creds.json")
    ap.add_argument("--tailscale", choices=["on", "off"], default="on")
    ap.add_argument("--ssh-fallback", choices=["on", "off"], default="off")
    ap.add_argument("--non-ai-target", default="", help="Optional node/group name for non-AI custom rules.")
    ap.add_argument("--no-listener", action="store_true", help="Skip 127.0.0.1:17941 dedicated listener.")
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    if not args.creds.is_file():
        print(f"ERROR: Credentials file not found: {args.creds}", file=sys.stderr)
        sys.exit(1)
    creds = json.loads(args.creds.read_text(encoding="utf-8"))
    js = generate_js(
        creds=creds,
        target_os=args.target_os,
        client=args.client,
        use_tailscale=(args.tailscale == "on"),
        use_ssh=(args.ssh_fallback == "on"),
        enable_listener=(not args.no_listener),
        non_ai_target_override=args.non_ai_target,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(js, encoding="utf-8")
    print(f"OK: Generated {args.client} ({args.target_os}) override JS at {args.output} "
          f"(tailscale={args.tailscale}, ssh_fallback={args.ssh_fallback})")


if __name__ == "__main__":
    main()
