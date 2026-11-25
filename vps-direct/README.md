# Direct VPS Multi-Protocol AI Proxy Kit (sing-box Reality + Hysteria2 + Tailscale Fallback)

一套零域名成本、高可用、全平台（Windows / macOS / Android FlClash / Linux 网关）的自建海外直连 VPS 代理方案，适用于 OpenAI / Codex / Grok / Gemini / Claude / Antigravity 等 AI 服务的低延迟、稳定直连。

---

## 1. 架构设计

```text
终端设备（Windows / macOS / Android）
  ├─ [主力] VLESS + XTLS-Vision + REALITY (TCP 443)  ──▶ 海外直连 VPS (sing-box + BBR)
  ├─ [提速] Hysteria2 (UDP 443)                      ──▶ 海外直连 VPS (sing-box + BBR)
  └─ [兜底] Tailscale 内网 SOCKS5 (17942)            ──▶ 海外直连 VPS (microsocks, 仅绑定 tailscale0)

国内中转 API 网关（如 CPA / sub2api，面向低带宽/限流量云主机）
  ├─ [主力] VLESS-Reality (TCP 443，无激进重传，省流量) ──▶ 海外直连 VPS
  └─ [兜底] Tailscale 内网 SOCKS5 (17942)               ──▶ 海外直连 VPS
```

### 为什么这样组合？
1. **彻底消除单连接 SSH `-D` 队头阻塞与 SOCKS5 额外 2-RTT 握手**：相比裸 SOCKS5 或 SSH 动态转发，VLESS-Reality 在跨洋 180–200ms 链路上单次建连可直接省下 ~350–420ms，支持 UDP 与并发流式 SSE/WebSocket；
2. **公网零域名零费用**：REALITY 无需自备域名和证书；Hysteria2 使用本地自签 ECDSA 证书并开启防探测伪装；
3. **不消耗国内云主机带宽与流量**：PC / Mac / 手机全部直连海外 VPS 公网 443，不经过国内中转网关；国内中转网关只转发轻量文本型 API 请求且禁用 Hysteria2；
4. **安全基线**：`sing-box` 以低权限用户运行、配置与私钥权限 `600`、路由层强制 `reject` 所有私有网段防 SSRF；兜底 `microsocks` 仅监听 Tailscale 私有网卡 `tailscale0`，公网不可见。

---

## 2. 服务端快速部署（海外 Ubuntu VPS）

### 2.1 内核网络调优（BBR + fq + 16MB 缓冲）
```bash
sudo modprobe tcp_bbr
echo "tcp_bbr" | sudo tee /etc/modules-load.d/bbr.conf
sudo cp server/sysctl-bbr-vps.conf /etc/sysctl.d/99-vps-network-tuning.conf
sudo sysctl -p /etc/sysctl.d/99-vps-network-tuning.conf
```
*(若为国内 5–10 Mbps 限速中转网关，改用 [`server/sysctl-bbr-gateway.conf`](server/sysctl-bbr-gateway.conf) 以防止小口子缓存膨胀。)*

### 2.2 安装 `sing-box` 并生成凭据
```bash
# 安装官方 sing-box (Debian/Ubuntu)
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://sing-box.app/gpg.key | sudo tee /etc/apt/keyrings/sagernet.asc >/dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/sagernet.asc] https://deb.sagernet.org/ * *" | sudo tee /etc/apt/sources.list.d/sagernet.list
sudo apt-get update && sudo apt-get install -y sing-box

# 生成 UUID、REALITY X25519 密钥对、ShortID 与 Hysteria2 强密码
sing-box generate uuid
sing-box generate reality-keypair
openssl rand -hex 8
openssl rand -hex 24

# 生成 Hysteria2 自签 ECDSA 证书
sudo openssl ecparam -name prime256v1 -genkey -noout -out /etc/sing-box/hy2.key
sudo openssl req -new -x509 -days 3650 -key /etc/sing-box/hy2.key -out /etc/sing-box/hy2.crt -subj "/CN=bing.com"
```

将 [`server/sing-box-config.example.json`](server/sing-box-config.example.json) 复制为 `/etc/sing-box/config.json`，填入上面生成的凭据，并收紧权限后启动：
```bash
sudo chown -R sing-box:sing-box /etc/sing-box
sudo chmod 750 /etc/sing-box && sudo chmod 600 /etc/sing-box/config.json /etc/sing-box/hy2.*
sudo sing-box check -c /etc/sing-box/config.json
sudo systemctl enable --now sing-box
```

### 2.3 部署 Tailscale 内网兜底（可选，推荐）
在海外 VPS 安装并加入你的 Tailscale / Headscale 组网后，部署仅绑定 `tailscale0` 的 `microsocks`：
```bash
sudo apt-get install -y microsocks
# 替换 <YOUR_TAILSCALE_VPS_IP> 后写入 systemd
sudo cp server/la-vps-tailscale-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now la-vps-tailscale-proxy.service
```

---

## 3. 客户端接入

* **Windows / macOS（Clash Party & Clash Verge 自动化接入 + Agent Skill）**：见 [`../skills/la-vps-client-onboarding/SKILL.md`](../skills/la-vps-client-onboarding/SKILL.md)
* **Android（FlClash 自包含模板）**：复制 [`android/flclash-vps-direct.example.yaml`](android/flclash-vps-direct.example.yaml)，填入占位符后导入 FlClash 即可（支持通过 `tailscale file cp` 安全传至手机）。
* **国内中转网关（`metacubexd` / `Mihomo`）**：参考 [`server/gateway-metacubexd-merge.example.yaml`](server/gateway-metacubexd-merge.example.yaml)。
