# Direct VPS Multi-Protocol AI Proxy & Onboarding Kit

一套面向 **多台电脑（Windows / macOS）+ 手机（Android FlClash）+ 国内轻量 API 网关（CPA / sub2api）** 的**自建海外直连 VPS** 代理与跨平台接入套件（**不依赖第三方静态住宅 ISP，无需自备域名，零额外费用**）：

- **双协议公网直连（零域名零证书）**：在海外直连 VPS 上通过 `sing-box` 同时开放 **`VLESS + XTLS-Vision + REALITY`（TCP 443 主力）** 与 **`Hysteria2`（UDP 443 晚高峰提速）**；相比单连接 SSH `-D` 或裸 SOCKS5，跨洋单次建连直接省下 ~350–420ms，原生支持 UDP 与高并发 SSE/WebSocket 流式输出。
- **Tailscale 私有内网兜底**：海外 VPS 同时在 `tailscale0` 私有网卡上常驻 `microsocks`（公网 `0.0.0.0` 不暴露任何端口），客户端配置为 `Reality → Hysteria2 → Tailscale` 三级自动容灾。
- **不消耗国内云主机带宽与流量**：Windows / macOS / Android 终端全部直连海外 VPS 公网 443；国内限速/限流量中转网关仅转发轻量文本型 API 请求，且强制只走省流量的 `Reality TCP 443` + `Tailscale`（禁用 Hysteria2）。
- **跨平台自动化接入 Skill**：内置 [`skills/la-vps-client-onboarding`](skills/la-vps-client-onboarding/SKILL.md)，覆盖 **Windows / macOS × Clash Party / Clash Verge**（含无 Python 家用 Windows 的纯 PowerShell 执行器），自动完成备份、最新全量 AI + 伴随风控域名分流注入、热重载与 5 项端到端脱敏验收。

---

## 1. 网络拓扑（直连 VPS 主力方案）

```text
┌───────────────────────────────────────────────────────────────────────────┐
│  个人终端（Windows / macOS：Clash Party / Clash Verge；Android：FlClash）  │
│    ├─ [主力] VLESS + XTLS-Vision + REALITY (TCP 443) ──▶ 海外直连 VPS     │
│    ├─ [提速] Hysteria2 (UDP 443)                     ──▶ 海外直连 VPS     │
│    ├─ [兜底] Tailscale 内网 SOCKS5 (17942)           ──▶ 海外直连 VPS     │
│    ├─ [直连] 国内站点 / 局域网 / 100.64.0.0/10 / 自建私有域名 ──▶ DIRECT   │
│    └─ [常规] 非 AI 海外流量                          ──▶ 本地订阅节点组    │
└───────────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────────┐
│  国内低带宽 API 网关（可选：CPA / sub2api + metacubexd + BBR/8MB）        │
│    ├─ [主力] VLESS-Reality (TCP 443，省流量无激进重传) ──▶ 海外直连 VPS   │
│    └─ [兜底] Tailscale 内网 SOCKS5 (17942)             ──▶ 海外直连 VPS   │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. 目录结构

```text
ai-isp-proxy-kit/
├── README.md
├── vps-direct/                                        # [主力] 自建海外直连 VPS 方案（非静态 ISP）
│   ├── README.md                                      # 服务端 BBR 调优 + sing-box 双协议 + Tailscale 兜底完整部署手册
│   ├── server/
│   │   ├── sysctl-bbr-vps.conf                        # 海外高带宽 VPS 内核调优（BBR + fq + 16MB 缓冲）
│   │   ├── sysctl-bbr-gateway.conf                    # 国内限速中转网关内核调优（BBR + fq + 8MB 防 Bufferbloat）
│   │   ├── sing-box-config.example.json               # sing-box 1.11+ 双协议服务端模板（Reality TCP 443 + Hy2 UDP 443 + 防 SSRF）
│   │   ├── la-vps-tailscale-proxy.service             # 仅绑定 tailscale0 的 microsocks 内网兜底 systemd 模板
│   │   └── gateway-metacubexd-merge.example.yaml      # 国内网关 metacubexd 省流量合并模板（仅 Reality TCP + Tailscale）
│   └── android/
│       └── flclash-vps-direct.example.yaml            # Android FlClash 自包含双协议 + AI/国内分流模板
├── skills/
│   └── la-vps-client-onboarding/                      # [主力] Windows / macOS 新电脑跨平台接入 Agent Skill
│       ├── SKILL.md                                   # 交互式接入工作流（Windows/macOS × Clash Party/Clash Verge + Tailscale）
│       ├── references/
│       │   ├── architecture_and_rules.md              # 双平台路径对照、Tailscale 接入与排错手册
│       │   └── vps-creds.example.json                 # 私有凭据 JSON 模板（零明文硬编码）
│       └── scripts/
│           ├── export_creds_from_host.py              # 从已配主机静默导出私有凭据并收紧 ACL/600 权限
│           ├── generate_override_js.py                # 跨平台覆写脚本生成器（自动适配 Windows/macOS 进程规则）
│           ├── apply_and_verify.py                    # 备份 + 注入 + Named Pipe/Unix Socket 热重载 + 端到端脱敏验收
│           └── apply_clash_windows.ps1                # 无 Python 环境的 Windows 零依赖 PowerShell 执行与验收脚本
└── [历史归档：静态 ISP 链式代理与防泄漏 Chrome 套件]
    ├── clash-verge/ai-isp-global-merge.yaml
    ├── windows/ (install-clash-verge-isp.ps1, start-isp-browser.ps1, *.cmd)
    ├── macos/start-isp-browser.sh
    └── server/ (mihomo-merge-template.yaml, bind-isp.sh, sub2api.env.example)
```

---

## 3. 快速上手

### 3.1 海外直连 VPS 服务端部署（一次部署，所有终端共用）
详见 [`vps-direct/README.md`](vps-direct/README.md)，核心只需 3 步：
1. 应用 [`vps-direct/server/sysctl-bbr-vps.conf`](vps-direct/server/sysctl-bbr-vps.conf) 开启 `BBR` + `fq` + `16MB` 缓冲 + 关闭空闲慢启动；
2. 安装官方 `sing-box`，基于 [`vps-direct/server/sing-box-config.example.json`](vps-direct/server/sing-box-config.example.json) 生成随机 UUID / X25519 密钥对 / ShortID / Hysteria2 密码并启动（监听公网 `443 TCP + UDP`，内置私有 IP 防 SSRF 拒绝规则）；
3. 安装 `microsocks` 并启用 [`vps-direct/server/la-vps-tailscale-proxy.service`](vps-direct/server/la-vps-tailscale-proxy.service)，仅监听 Tailscale 私有网卡 `17942` 作为内网兜底。

### 3.2 新电脑接入（Windows / macOS × Clash Party / Clash Verge）
将 [`skills/la-vps-client-onboarding`](skills/la-vps-client-onboarding/SKILL.md) 放入本地 Agent Skill 目录，或按模板 [`vps-creds.example.json`](skills/la-vps-client-onboarding/references/vps-creds.example.json) 准备好本机私有凭据 `~/.config/la-vps-proxy/vps-creds.json`（权限 `600`）后运行：

```bash
# Windows / macOS 通用（自动备份 + 生成覆写 + 热重载 + 端到端实测）
python skills/la-vps-client-onboarding/scripts/apply_and_verify.py \
  --os <windows|macos> \
  --client <clash-party|clash-verge> \
  --creds ~/.config/la-vps-proxy/vps-creds.json \
  --tailscale on
```

若目标 Windows 电脑未安装 Python，可先在控制机用 `generate_override_js.py` 生成覆写 `.js`，再传至目标机执行零依赖的 PowerShell 脚本：
```powershell
powershell -ExecutionPolicy Bypass -File apply_clash_windows.ps1 -Client clash-verge -OverrideJsPath .\Script.js -TailscaleVpsIp <YOUR_TAILSCALE_VPS_IP>
```

### 3.3 Android 手机接入（FlClash）
复制 [`vps-direct/android/flclash-vps-direct.example.yaml`](vps-direct/android/flclash-vps-direct.example.yaml)，替换 `<YOUR_*>` 占位符后导入 **FlClash**（可通过 `tailscale file cp` 安全发送至手机）。开启 FlClash 时 Android 会自动暂停 Tailscale VPN，公网 `443` Reality / Hysteria2 直接走 4G/5G/Wi-Fi 工作，无需常开 Tailscale。

### 3.4 国内中转 API 网关（CPA / sub2api，可选）
将 [`vps-direct/server/gateway-metacubexd-merge.example.yaml`](vps-direct/server/gateway-metacubexd-merge.example.yaml) 合入网关的 `metacubexd` / Mihomo 覆写模板，仅使用省流量的 `Reality TCP 443` + `Tailscale` 兜底，并应用 [`vps-direct/server/sysctl-bbr-gateway.conf`](vps-direct/server/sysctl-bbr-gateway.conf)。

---

## 4. 核心设计要点

1. **全量 AI + 伴随风控域名统一收口**：不仅代理 OpenAI / ChatGPT / Codex / Grok / Gemini / Claude / Meta 主域名，同时将 `challenges.cloudflare.com`、`arkoselabs.com`、`accounts.google.com`、`oauth2.googleapis.com`、`auth.meta.com`、`statsigapi.net`、`featuregates.org` 统一收口到同一 VPS 出口，避免主站与人机盾/登录页出口 IP 不一致导致无限验证循环。
2. **Tailscale 防环路与私有域名直连**：规则置顶包含 `IP-CIDR,100.64.0.0/10,DIRECT,no-resolve` 与用户自定义的 `direct_domains`，确保 Tailscale 组网与国内自建 API 网关毫秒直连，绝不绕行海外 VPS。
3. **17941 专用监听口**：提供 `127.0.0.1:17941` 独立 Mixed 监听口直绑 `Antigravity-VPS`，供需要固定走直连 VPS 的应用或 CLI 显式指定。

---

## 5. 历史归档：静态住宅 ISP 链式代理与防泄漏 Chrome 套件

仓库根目录保留的 `clash-verge/`、`windows/`、`macos/`、`server/` 为早期「静态住宅 ISP 链式代理 + 17899 纯净防泄漏 Chrome（WebRTC / DNS / 时区隔离）」方案归档，适合确有独享静态住宅 ISP 链式落地或独立浏览器防泄漏需求时参考复用：
- 独立 Chrome 启动器在拉起前直接写入 `Default/Preferences` 禁用非代理 WebRTC UDP（`disable_non_proxied_udp`），配合 `--enforce-webrtc-ip-permission-check` 清零本地 ICE 候选。
- 通过 `17899` 纯净端口绕过分流规则，保证环境检测站单出口一致。

---

## 6. 安全与隐私约定

- 仓库内全部文件均已彻底脱敏，所有服务器地址、UUID、X25519 公私钥、ShortID、密码、私有域名均使用 `<YOUR_*>` 占位符或由运行时私有文件 `~/.config/la-vps-proxy/vps-creds.json` 读取。
- **切勿将真实的 `vps-creds.json`、个人订阅链接、服务器公网 IP 或 GitHub PAT 提交到任何公开仓库**。
