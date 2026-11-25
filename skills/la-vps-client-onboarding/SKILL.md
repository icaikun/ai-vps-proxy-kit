---
name: la-vps-client-onboarding
description: >-
  跨平台（Windows / macOS）新电脑一键接入自建海外直连 VPS（VLESS-Reality TCP 443 + Hysteria2 UDP 443 + Tailscale 内网兜底）的交互式配置工作流。
  支持 Clash Party 与 Clash Verge 双客户端，自动生成最新全量 AI/Codex/Grok/Gemini/Claude/Meta 分流覆写脚本、配置 Tailscale 兜底并做端到端实测验证。
  当用户要给新电脑（Windows 或 macOS）配置直连 VPS 代理、同步最新 VPS 节点与 AI 分流规则、或为新机器接入 Tailscale 兜底时使用。
---

# 自建直连 VPS 新电脑跨平台接入指南（Windows / macOS × Clash Party / Clash Verge）

本 Skill 用于将任意新的 **Windows** 或 **macOS** 电脑快速、安全、无损地接入已部署好的海外直连 VPS 链路：
- **主力通道**：`VLESS + XTLS-Vision + REALITY`（TCP 443，抗限速、免域名、零额外握手 RTT、支持 UDP）
- **高速备选**：`Hysteria2`（UDP 443，高丢包晚高峰提速）
- **内网兜底**：`Tailscale` 私有加密网口上的 `microsocks`（`<YOUR_TAILSCALE_VPS_IP>:17942`，公网 443 极端故障时自动接管）
- **直连保护**：内置 `IP-CIDR,100.64.0.0/10,DIRECT,no-resolve`（Tailscale 防环路）与可配置私有直连域名列表（如自建 API 网关域名，避免绕行海外）。

> [!CAUTION]
> **安全与凭据红线（强制遵守）**
> 1. **严禁**在聊天回复、终端回显、Markdown 文档、Skill 文件或 Git 仓库中打印明文 VPS 公网 IP、UUID、REALITY `public-key`/`short-id`、Hysteria2 密码、Tailscale authkey 或订阅链接。
> 2. 所有节点凭据仅存储在目标机器私有目录 `~/.config/la-vps-proxy/vps-creds.json`（Linux/macOS 目录 `700`、文件 `600`；Windows 用 `icacls` 仅限当前用户与 `SYSTEM` 访问）。

---

## 执行工作流

### 第 1 步：交互确认目标环境（必做）
在改动任何配置之前，向用户确认以下关键选项（若已在目标机器本地运行，可先自动探测 OS 和已安装客户端，再请用户确认）：

1. **目标操作系统**：`Windows` / `macOS`
2. **目标代理客户端**：`Clash Party (mihomo-party)`（推荐）/ `Clash Verge (clash-verge-rev)`
3. **是否配置 Tailscale 内网兜底**：
   - `是，接入 Tailscale / 自建 Headscale 并启用 VPS 内网 17942 兜底`（推荐）
   - `否，仅使用公网 Reality TCP 443 + Hysteria2 UDP 443`
4. **本地凭据来源**（仅当目标机尚无 `~/.config/la-vps-proxy/vps-creds.json` 时询问）：
   - 从已配置好的主机安全复制 `vps-creds.json`（如经 Tailscale SCP / Taildrop 等私有加密通道）
   - 或参照 [vps-creds.example.json](./references/vps-creds.example.json) 在本机手动创建并收紧权限

---

### 第 2 步：准备私有凭据（零明文回显）
检查目标机是否存在 `~/.config/la-vps-proxy/vps-creds.json`：
- 若当前主机已配置好 Clash Party / Clash Verge，运行导出脚本静默提取凭据到私有文件（不打印任何明文）：
  ```bash
  python scripts/export_creds_from_host.py --from-local
  ```
- 若要分发给另一台新电脑：通过私有加密通道（如 Tailscale `scp`）将 `~/.config/la-vps-proxy/vps-creds.json` 传至目标机同路径并收紧权限，**禁止通过公网聊天或公开仓库传递**。

---

### 第 3 步：配置 Tailscale 兜底（若第 1 步选启用）
详细命令见 [architecture_and_rules.md](./references/architecture_and_rules.md#4-tailscale-兜底接入流程)：
1. **检查安装**：执行 `tailscale version`（macOS 如不在 `$PATH` 中，检查 `/Applications/Tailscale.app/Contents/MacOS/Tailscale`）。
2. **接入组网**：使用 `tailscale up --login-server=https://<YOUR_HEADSCALE_HOST> --accept-routes=false`（或官方 Tailscale 登录）。
3. **验证兜底通道**：确认 `tailscale ping -c 2 <vps-node-name>` 返回 `pong`，且 `<YOUR_TAILSCALE_VPS_IP>:17942` 端口连通。

---

### 第 4 步：生成并应用客户端覆写配置（自动备份 + 校验 + 热重载）

1. **生成最新覆写脚本**（纯 Python 标准库，无明文打印）：
   ```bash
   python scripts/generate_override_js.py \
     --os <windows|macos> \
     --client <clash-party|clash-verge> \
     --creds ~/.config/la-vps-proxy/vps-creds.json \
     --tailscale <on|off> \
     --output <target_js_path>
   ```
   - 自动构建 `Antigravity-VPS` `fallback` 组：`Antigravity-VPS-Reality` → `Antigravity-VPS-Hy2` → `Antigravity-VPS-TS`（可选）→ `Antigravity-VPS-SSH`（仅当检测到本地 `127.0.0.1:17942` SSH 隧道时自动追加）。
   - 自动注入全量 AI + 伴随风控域名分流规则（OpenAI/Codex、Grok/xAI、Gemini/Google AI、Claude/Anthropic、Meta/Muse、Cursor/Perplexity、`challenges.cloudflare.com`、`accounts.google.com`、`auth.meta.com`）与 `127.0.0.1:17941` 专用监听器。
   - **Windows 与 macOS 进程规则自动隔离**：macOS 仅写入 macOS 进程/应用路径，绝不混入 Windows 盘符路径。

2. **自动备份、注入与热重载**：
   - **有 Python 环境（Windows / macOS 通用）**：
     ```bash
     python scripts/apply_and_verify.py \
       --os <windows|macos> \
       --client <clash-party|clash-verge> \
       --creds ~/.config/la-vps-proxy/vps-creds.json \
       --tailscale <on|off>
     ```
   - **无 Python 的普通 Windows 电脑**：先在任意有 Python 的控制机用 `generate_override_js.py` 生成目标覆写 `.js`，再将生成的 `.js` 与零依赖的 [apply_clash_windows.ps1](./scripts/apply_clash_windows.ps1) 传至目标 Windows 运行（兼容 Clash Verge 2.5+ 哈希 Named Pipe 与 Clash Party Pipe）：
     ```powershell
     powershell -ExecutionPolicy Bypass -File apply_clash_windows.ps1 -Client clash-verge -OverrideJsPath .\Script.js -TailscaleVpsIp <YOUR_TAILSCALE_VPS_IP>
     ```

---

### 第 5 步：端到端验收门禁（全部通过才算完成）
执行 `apply_and_verify.py --verify-only`（或在 apply 后自动执行），核对以下指标（输出严格脱敏）：

1. **实时节点存活与延迟**：`Antigravity-VPS-Reality`（TCP 443）、`Antigravity-VPS-Hy2`（UDP 443）、`Antigravity-VPS-TS`（如启用）延迟正常，且 `Antigravity-VPS` 主选为 `Antigravity-VPS-Reality`。
2. **OpenAI / Codex 连通**：经本地代理访问 `https://api.openai.com/v1/models`（`HTTP 401`）与 `https://chatgpt.com/backend-api/codex/responses`（`HTTP 405`）。
3. **Grok / Gemini / CF 验证连通**：`https://grok.com/`、`https://gemini.google.com/`、`https://challenges.cloudflare.com/` 均返回 `HTTP 200`。
4. **私有域名直连保护**（如在 `vps-creds.json` 中配置了 `direct_domains` / `direct_check_url`）：确认命中 `DIRECT` 规则，直连不绕行海外。
5. **Tailscale 兜底验证**（如启用）：`tailscale ping` 成功且 `socks5h://<YOUR_TAILSCALE_VPS_IP>:17942` 可直通 `api.openai.com`。

---

## 参考文档
- [架构、双平台路径与排错清单](./references/architecture_and_rules.md)
- [私有凭据 JSON 示例模板](./references/vps-creds.example.json)
