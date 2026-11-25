# AI Static ISP Chained Proxy & Anti-Leak Browser Kit

一套用于**多电脑 + 云端网关（`sub2api` / `Mihomo`）共用独享静态住宅 ISP** 的零指纹客户端方案：
- **任意梯子自动接力静态 ISP**：利用 Mihomo 原生 `dialer-proxy` + `include-all: true`，无论你电脑当前导入了哪家机场订阅（港/日/新/美节点），访问主流海外 AI 与伴随风控域名时自动链式落地到你的独享静态 ISP；平时看视频/刷网页仍走本地高速机场，互不干扰。
- **独立 17899 纯净浏览器端口 + WebRTC/DNS/时区全隔离**：不用装任何高危反关联插件，直接用官方原版 Chrome 独立 `user-data-dir` 配合全局无分流端口，彻底解决多出口不一致、WebRTC UDP 泄漏、DNS 泄漏与时区冲突。
- **云端容器网关对齐**：提供国内 VPS 上 `Mihomo + sub2api` 的时区/语言/DNS 防泄漏与一键换绑 ISP 脚本模板。

---

## 1. 网络拓扑

```text
┌────────────────────────────────────────────────────────────────────┐
│  多台电脑（API 客户端：Claude Code / Cursor / Cherry Studio）        │
│    └─ 直连 HTTPS ─▶ 云端 VPS (sub2api, TZ=America/Los_Angeles)      │
│                        └─ 本地 Mihomo (Rule 模式)                  │
│                             └─ 加密前置节点 ─▶ 独享静态住宅 ISP      │
└────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────┐
│  多台电脑（网页版 / OAuth 授权：原版 Chrome 独立档案）              │
│    ├─ 方案 A（高速本机直出，推荐）：                                │
│    │     纯净 Chrome ─▶ 本机 17899 纯净端口 ─▶ 任意机场 ─▶ 静态 ISP │
│    └─ 方案 B（SSH 隧道复用 VPS 出口）：                             │
│          纯净 Chrome ─▶ SSH LocalForward ─▶ VPS 17899 ─▶ 静态 ISP  │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. 目录结构

```text
ai-isp-proxy-kit/
├── README.md
├── clash-verge/
│   └── ai-isp-global-merge.yaml       # Clash Verge Rev / Mihomo Party 全局扩展覆写模板
├── windows/
│   ├── install-clash-verge-isp.ps1    # Windows 新电脑一键部署脚本（写覆写 + 校验 + 生成启动器）
│   ├── start-isp-browser.ps1          # Windows 纯净 Chrome 启动器（防 WebRTC + 临时对齐时区）
│   ├── 启动纯净AI浏览器.cmd            # 双击入口
│   └── 恢复北京时间.cmd               # 异常关闭时的时区一键兜底脚本
├── macos/
│   └── start-isp-browser.sh           # macOS 纯净 Chrome 启动器（TZ 环境变量 + 防 WebRTC）
├── server/
│   ├── mihomo-merge-template.yaml     # VPS Mihomo / metacubexd 覆写模板（含 17899 端口与防 DNS 泄漏）
│   ├── bind-isp.sh                    # VPS 一键更新/换绑静态 ISP 脚本
│   └── sub2api.env.example            # sub2api 容器加州时区与英文 Locale 环境变量示例
├── vps-direct/                        # [新增] 自建海外直连 VPS 多协议方案（免域名零费用）
│   ├── README.md                      # 服务端内核 BBR 调优 + sing-box 双协议 + Tailscale 兜底部署指南
│   ├── server/
│   │   ├── sysctl-bbr-vps.conf        # 海外高带宽 VPS 内核调优（BBR + fq + 16MB 缓冲）
│   │   ├── sysctl-bbr-gateway.conf    # 国内限速中转网关内核调优（BBR + fq + 8MB 防 Bufferbloat）
│   │   ├── sing-box-config.example.json          # VLESS-Reality (TCP 443) + Hysteria2 (UDP 443) + 防 SSRF 模板
│   │   ├── la-vps-tailscale-proxy.service        # Tailscale 内网兜底 microsocks systemd 服务模板
│   │   └── gateway-metacubexd-merge.example.yaml # 国内中转网关省流量合并模板（仅 Reality TCP + Tailscale）
│   └── android/
│       └── flclash-vps-direct.example.yaml       # Android FlClash 自包含双协议 + AI/国内分流模板
└── skills/
    └── la-vps-client-onboarding/      # [新增] Windows / macOS 新电脑跨平台接入 Agent Skill
        ├── SKILL.md                   # 交互式接入流程（Clash Party / Clash Verge + Tailscale 兜底）
        ├── references/                # 双平台路径对照、排错清单与私有凭据 JSON 模板
        └── scripts/                   # 凭据安全导出、覆写生成、跨平台热重载验收 & 无 Python Windows 执行器
```

> **新增方案说明**：除原有的「静态住宅 ISP 链式代理」外，本仓库现已补充 **自建直连 VPS 多协议方案**（[`vps-direct/`](vps-direct/README.md)）及配套跨平台 Agent Skill（[`skills/la-vps-client-onboarding/`](skills/la-vps-client-onboarding/SKILL.md)）：支持海外 VPS 上零域名部署 `sing-box`（`VLESS-Reality TCP 443` + `Hysteria2 UDP 443`）+ `BBR/fq` 调优 + Tailscale 私有内网兜底，覆盖 **Windows / macOS（Clash Party & Clash Verge）、Android（FlClash）与国内 API 网关（省流量模式）**。

---

## 3. 快速上手（新电脑 1 分钟部署）

### Windows（Clash Verge Rev）

1. 确保新电脑已经装好 **Clash Verge Rev** 和 **Google Chrome**，并任意导入并启用了一个可用的机场订阅。
2. 在 PowerShell 运行一键脚本（把占位符换成你自己的静态 ISP 信息）：

```powershell
cd windows
powershell -ExecutionPolicy Bypass -File .\install-clash-verge-isp.ps1 `
  -IspType socks5 `
  -IspServer "<YOUR_ISP_IP>" `
  -IspPort 1080 `
  -IspUser "<YOUR_ISP_USER>" `
  -IspPass "<YOUR_ISP_PASS>"
```

脚本会自动备份原有的 `Merge.yaml`，写入全量 AI + 伴随风控域名的链式覆写规则，调用 `verge-mihomo.exe -t` 校验语法，并生成桌面/同目录可双击的 `启动纯净AI浏览器.cmd`。

3. 如果你的新电脑另外还运行了 **Clash Party (Mihomo Party)** 在 `7890` 端口：只需在 Clash Verge 启用 `AI-ISP`，然后让 Clash Party 覆写脚本将 AI 域名转发至 `127.0.0.1:7897` 即可共用。

### macOS

1. 在 Clash Verge Rev 的 **订阅 ➔ 全局扩展覆写配置（Merge）** 中粘贴 [`clash-verge/ai-isp-global-merge.yaml`](clash-verge/ai-isp-global-merge.yaml) 并填入你的静态 ISP 参数。
2. 赋予执行权限并启动纯净 Chrome：

```bash
chmod +x macos/start-isp-browser.sh
./macos/start-isp-browser.sh
```

*(macOS 下的 Chromium 会直接尊重进程级 `TZ=America/Los_Angeles`，无需修改系统时钟。)*

---

## 4. 关键防坑说明

### 4.1 为什么分流规则必须包含“伴随风控域名”？
仅代理 `claude.ai` / `chatgpt.com` 主域名远远不够。打开网页或绑卡时，客户端还会同时请求：
- 人机验证盾：`challenges.cloudflare.com`、`arkoselabs.com`、`hcaptcha.com`、`recaptcha.net`
- 统一登录 SSO：`auth0.com`、`workos.com`、`clerk.com`、`accounts.google.com`
- 支付与实名风控：`stripe.com`、`stripe.network`、`withpersona.com`
- 遥测与灰度指纹：`statsig.com`、`statsigapi.net`、`featuregates.org`、`intercom.io`

如果主站走静态 ISP 而这些伴随域名走普通机场，极易触发无限跳盾或拒付风控。模板中已将上述域名全部收口至 `AI-ISP`。

### 4.2 为什么单独开了一个 `17899` 纯净全局端口？
环境检测站（如 `ping0.cc/env`）的多出口探针会同时请求国内站点（微信、抖音、网易云）和海外站点（Cloudflare、ipify）来比对是否开了分流 VPN。
- 日常使用 `7897`（Rule 分流模式）：国内直连、AI 走静态 ISP、视频走机场高速节点。
- 纯净 Chrome 专窗走 `17899`（绑定 `proxy: "🇺🇸 独享静态ISP"` 的独立 Listener）：**绕过任何分流规则**，保证浏览器内发出的每一个请求都只从唯一静态 ISP 出口出去，同时不影响宿主机其他软件的正常网络。

### 4.3 为什么 Chrome 157 不能只传 `--force-webrtc-ip-handling-policy`？
实测在较新的 Chrome 稳定版中，单独传命令行参数 `--force-webrtc-ip-handling-policy=disable_non_proxied_udp` 会被忽略（依然会发出本地 UDP ICE 候选导致暴露真实公网 IP）。
本工具的启动器会在每次拉起 Chrome 前直接向独立档案的 `Default/Preferences` 写入：

```json
"webrtc": {
  "ip_handling_policy": "disable_non_proxied_udp",
  "multiple_routes_enabled": false,
  "nonproxied_udp_enabled": false
}
```

并配合 `--enforce-webrtc-ip-permission-check`，实测可彻底将 WebRTC ICE 候选清零（`[]`）。

### 4.4 识别 `ping0.cc/env` 常见误报（千万别为了刷分乱装伪装插件）
1. **UA 版本 ↔ 启发式检测版本**：当你的真实 Chrome 版本更新快于 `ping0.cc` 特征探针库上限（例如 Chrome 157 对探针上限 151）时，会误报“致命”。**绝对不要**为了刷分去装插件把 UA 改低，真实站点反而会抓到 TLS 指纹与低 UA 不符。
2. **DNS 黑洞 (`resolver_count=0`)**：`ping0.cc/env` 通过随机子域 `*.d.ping0.cc` 探测上游 DNS；当其权威服务器 `x.leak.ping0.cc` 自身不可达或拒绝连接时，页面会报 `resolver_count=0` 并误标为“DNS 黑洞”。遇到此情况请用 `https://ipleak.net` 或 `https://browserleaks.com/dns` 交叉验证。
3. **IP 国家 ↔ 中文字体 (`has_cn_fonts=true`)**：检测到 Windows 中文字体属于一般提示（主要针对跨境电商防店群），对 AI 平台无影响。

---

## 5. 安全与隐私约定

- 仓库中所有配置均使用 `<YOUR_ISP_*>` 占位符，**切勿将真实的静态 ISP 账密、个人机场订阅链接或服务器公网 IP 提交到公开仓库**。
- 切勿使用来路不明的第三方修改版指纹浏览器来登录核心 AI 账号。
