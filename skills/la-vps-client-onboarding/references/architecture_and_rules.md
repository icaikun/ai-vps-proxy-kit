# 自建直连 VPS 客户端接入参考手册（Windows / macOS）

## 1. 服务端架构总览（一次部署，新电脑无需再改服务端）

| 节点 | 角色 | 已部署能力 | 备注 |
| :--- | :--- | :--- | :--- |
| **海外直连 VPS** | 公网直连出口 + 内网兜底 | `sing-box`（`TCP 443` VLESS+XTLS-Vision+REALITY + `UDP 443` Hysteria2）+ `microsocks`（仅绑定 Tailscale `17942`）+ `BBR/fq/16MB` 内核调优 | 终端直连公网 443，不经过国内中转机 |
| **国内中转网关（可选）** | Headscale 控制面 + API 网关（如 CPA / sub2api） | `headscale` + `metacubexd`（仅接省流量 `VPS-Reality` TCP 443 + `Tailscale` 备选）+ `BBR/fq/8MB` | 适合低带宽/限流量云主机，仅承载轻量文本型 API |

---

## 2. 各平台 × 客户端配置路径对照表

### Windows
| 客户端 | 数据目录 | 持久化覆写入口 | 运行时配置 | 本地控制接口 | 默认代理端口 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clash Party** (`mihomo-party`) | `%APPDATA%\mihomo-party` | `override\la-vps-ai-routing.js`（并在 `override.yaml` 注册 `global: true`） | `work\config.yaml` | Named Pipe `\\.\pipe\MihomoParty\mihomo-*` | `7890`（+ `17941` 专用口） |
| **Clash Verge** (`clash-verge-rev`) | `%APPDATA%\io.github.clash-verge-rev.clash-verge-rev` | `profiles\Script.js` | `clash-verge.yaml` | Named Pipe `\\.\pipe\verge-mihomo` 或 `verge-mihomo-sidecar-*` | `7897`（+ `17941` 专用口） |

### macOS
| 客户端 | 数据目录 | 持久化覆写入口 | 运行时配置 | 本地控制接口 | 默认代理端口 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clash Party** (`mihomo-party`) | `~/Library/Application Support/mihomo-party` | `override/la-vps-ai-routing.js`（并在 `override.yaml` 注册 `global: true`） | `work/config.yaml` | Unix Socket `/tmp/mihomo-party.sock` | `7890`（+ `17941` 专用口） |
| **Clash Verge** (`clash-verge-rev`) | `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev` | `profiles/Script.js` | `clash-verge.yaml` | Unix Socket `/tmp/verge/verge-mihomo.sock` | `7897`（+ `17941` 专用口） |

---

## 3. 私有凭据文件 (`~/.config/la-vps-proxy/vps-creds.json`)

模板见 [vps-creds.example.json](./vps-creds.example.json)。该文件**仅保存在本机私有目录**，禁止提交 Git 或在终端/日志中明文回显。

可选扩展字段：
- `direct_domains`：强制直连的私有域名后缀列表（例如自建 API 网关或 Headscale 根域名），将置顶写入 `DIRECT` 规则，确保不绕行海外。
- `direct_check_url`：验收脚本用于测试私有直连保护的探活 URL（可选）。
- `non_ai_target`：非 AI 自定义规则（PayPal / Google / ping0 / recaptcha）的指定代理节点或组名；留空时脚本自动从当前订阅匹配常见代理组。
- `tailscale_vps_node`：Tailscale 中的海外 VPS 节点名（默认 `la-vps`），用于验收时执行 `tailscale ping`。

---

## 4. Tailscale 兜底接入流程

### 安装
- **Windows**：`winget install -e --id Tailscale.Tailscale`
- **macOS**：`brew install --cask tailscale`（或从 App Store / 官网安装；CLI 位于 `/Applications/Tailscale.app/Contents/MacOS/Tailscale`）

### 加入自建 Headscale（或官方 Tailscale）
1. **命令行接入自建 Headscale**：
   ```bash
   tailscale up --login-server=https://<YOUR_HEADSCALE_HOST> --accept-routes=false
   ```
   若需服务端审批，在 Headscale 宿主机执行：
   ```bash
   headscale nodes register --user <YOUR_USER> --key <mkey:...>
   ```
2. **免交互一次性预认证 Key**：
   ```bash
   # 在 Headscale 宿主机生成短期 key
   headscale preauthkeys create --user <YOUR_USER> --expiration 30m
   # 在新电脑运行
   tailscale up --login-server=https://<YOUR_HEADSCALE_HOST> --authkey <KEY> --accept-routes=false
   ```
3. **验证**：
   ```bash
   tailscale status
   tailscale ping -c 2 <YOUR_VPS_TAILSCALE_NODE>
   ```

---

## 5. 常见排错

| 现象 | 原因 | 排查与处理 |
| :--- | :--- | :--- |
| `Antigravity-VPS-Reality` 偶发超时 | 热重载后首次探测抖动或本地防火墙拦截 | 复测 `delay`；确认 `Antigravity-VPS` 自动回退至 `Hy2` 或 `TS` |
| `Antigravity-VPS-Hy2` 超时但 `Reality` 正常 | 运营商晚高峰限速/丢弃 UDP 443 | 属正常现象，默认 `Reality` 排第一顺位不受影响 |
| `Antigravity-VPS-TS` 超时 | 新电脑 Tailscale 未上线或未加入组网 | 运行 `tailscale status` 与 `tailscale ping` 检查连通性 |
| 私有网关域名延迟偏高（> 500ms） | 未加入 `direct_domains` 被误绕行海外 | 将根域名加入 `vps-creds.json` 的 `direct_domains` 后重新生成 |
| Clash Party 刷新订阅后覆写未生效 | 未在 `override.yaml` 注册全局覆写脚本 | 确保 `override.yaml` 已启用 `global: true` 指向生成的 `.js` 脚本 |
