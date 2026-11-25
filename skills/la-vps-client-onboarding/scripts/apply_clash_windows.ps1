<#
.SYNOPSIS
Zero-Python Windows helper for la-vps-client-onboarding skill.
Backs up existing Clash Party / Clash Verge override JS, applies generated JS,
queries live Mihomo Named Pipe (supports Clash Verge 2.5+ sidecar hash pipes
and Clash Party pipes), and runs end-to-end redacted verification.
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("clash-party", "clash-verge")]
    [string]$Client,

    [string]$OverrideJsPath = "",
    [string]$TailscaleVpsIp = "",
    [string]$TailscaleVpsNode = "la-vps",
    [int]$TailscaleVpsPort = 17942,
    [string]$DirectCheckUrl = "",
    [int]$ProxyPort = 0,
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

function Redact-Text([string]$s) {
    if (-not $s) { return "" }
    return [regex]::Replace($s, '\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b', {
        param($m)
        $a = $m.Groups[1].Value
        if ($a -in @('127','192','10')) { return $m.Value }
        return "$a.*.*.$($m.Groups[4].Value)"
    })
}

function Find-MihomoPipe([string]$clientType) {
    $pipes = [System.IO.Directory]::GetFiles("\\.\pipe\")
    if ($clientType -eq "clash-party") {
        foreach ($p in $pipes) {
            if ($p -match '\\MihomoParty\\mihomo') { return $p }
        }
    } else {
        foreach ($p in $pipes) {
            if ($p -match '\\verge-mihomo(-sidecar-.*)?$') { return $p }
        }
    }
    return $null
}

function Invoke-PipeHttp([string]$pipeFullPath, [string]$method, [string]$reqPath, [string]$jsonBody = $null) {
    $pipeName = $pipeFullPath -replace '^\\\\\.\\pipe\\', ''
    $client = New-Object System.IO.Pipes.NamedPipeClientStream(".", $pipeName, [System.IO.Pipes.PipeDirection]::InOut)
    try {
        $client.Connect(5000)
        $payloadBytes = if ($jsonBody) { [System.Text.Encoding]::UTF8.GetBytes($jsonBody) } else { [byte[]]@() }
        $hdr = "$method $reqPath HTTP/1.1`r`nHost: localhost`r`nContent-Type: application/json`r`nContent-Length: $($payloadBytes.Length)`r`nConnection: close`r`n`r`n"
        $hdrBytes = [System.Text.Encoding]::UTF8.GetBytes($hdr)
        $client.Write($hdrBytes, 0, $hdrBytes.Length)
        if ($payloadBytes.Length -gt 0) {
            $client.Write($payloadBytes, 0, $payloadBytes.Length)
        }
        $client.Flush()
        $ms = New-Object System.IO.MemoryStream
        $buf = New-Object byte[] 65536
        while ($true) {
            $n = $client.Read($buf, 0, $buf.Length)
            if ($n -le 0) { break }
            $ms.Write($buf, 0, $n)
        }
        $raw = [System.Text.Encoding]::UTF8.GetString($ms.ToArray())
        $parts = $raw -split "`r`n`r`n", 2
        $statusLine = ($parts[0] -split "`r`n")[0]
        $body = if ($parts.Length -gt 1) { $parts[1] } else { "" }
        if ($parts[0] -match '(?i)Transfer-Encoding:\s*chunked') {
            $lines = $body -split "`r`n"
            $sb = New-Object System.Text.StringBuilder
            for ($i = 0; $i -lt $lines.Length - 1; $i += 2) {
                $lenHex = ($lines[$i] -split ';')[0].Trim()
                if ($lenHex -eq '0' -or -not $lenHex) { break }
                if ($i + 1 -lt $lines.Length) { [void]$sb.Append($lines[$i + 1]) }
            }
            $body = $sb.ToString()
        }
        return @{ Status = $statusLine; Body = $body.Trim() }
    } finally {
        $client.Dispose()
    }
}

$clientDir = if ($Client -eq "clash-party") {
    Join-Path $env:APPDATA "mihomo-party"
} else {
    Join-Path $env:APPDATA "io.github.clash-verge-rev.clash-verge-rev"
}
if ($ProxyPort -eq 0) {
    $ProxyPort = if ($Client -eq "clash-party") { 7890 } else { 7897 }
}

if (-not $VerifyOnly) {
    if (-not (Test-Path $clientDir)) { throw "Client directory not found: $clientDir" }
    if (-not $OverrideJsPath -or -not (Test-Path $OverrideJsPath)) { throw "OverrideJsPath not found: $OverrideJsPath" }

    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $bkDir = Join-Path $clientDir "backups\la-vps-onboarding-$ts"
    New-Item -ItemType Directory -Path $bkDir -Force | Out-Null

    if ($Client -eq "clash-verge") {
        $targetJs = Join-Path $clientDir "profiles\Script.js"
        if (Test-Path $targetJs) { Copy-Item $targetJs (Join-Path $bkDir "Script.js") -Force }
        Copy-Item $OverrideJsPath $targetJs -Force
        Write-Output "[APPLY] Updated Clash Verge Script.js (backup: $bkDir)"
    } else {
        $ovDir = Join-Path $clientDir "override"
        New-Item -ItemType Directory -Path $ovDir -Force | Out-Null
        $targetJs = Join-Path $ovDir "la-vps-ai-routing.js"
        if (Test-Path $targetJs) { Copy-Item $targetJs (Join-Path $bkDir "la-vps-ai-routing.js") -Force }
        Copy-Item $OverrideJsPath $targetJs -Force
        Write-Output "[APPLY] Updated Clash Party override: $targetJs (backup: $bkDir)"
    }
}

Write-Output "=== LIVE MIHOMO API CHECK ($Client) ==="
$pipe = Find-MihomoPipe $Client
if ($pipe) {
    Write-Output "  Pipe detected: OK"
    try {
        $grp = Invoke-PipeHttp $pipe "GET" "/proxies/Antigravity-VPS"
        $gd = $grp.Body | ConvertFrom-Json
        Write-Output ("  [LIVE GROUP] Antigravity-VPS -> now=" + $gd.now + " all=" + ($gd.all -join ", "))
    } catch {
        Write-Output ("  [LIVE GROUP] Error: " + $_.Exception.Message)
    }
    foreach ($n in @("Antigravity-VPS-Reality", "Antigravity-VPS-Hy2", "Antigravity-VPS-TS")) {
        try {
            $d = Invoke-PipeHttp $pipe "GET" "/proxies/$n/delay?timeout=5000&url=https://www.gstatic.com/generate_204"
            Write-Output ("  [NODE DELAY] {0,-24}: {1}" -f $n, $d.Body)
        } catch {
            Write-Output ("  [NODE DELAY] {0,-24}: ERR {1}" -f $n, $_.Exception.Message)
        }
    }
} else {
    Write-Output "  [WARN] Mihomo pipe not found; reload client UI to activate."
}

Write-Output "`n=== END-TO-END HTTP CHECK VIA 127.0.0.1:$ProxyPort ==="
$checks = @(
    @{ Name="api.openai.com";  Url="https://api.openai.com/v1/models" },
    @{ Name="codex responses"; Url="https://chatgpt.com/backend-api/codex/responses" },
    @{ Name="grok.com";        Url="https://grok.com/" },
    @{ Name="gemini.google";   Url="https://gemini.google.com/" },
    @{ Name="challenges.cf";   Url="https://challenges.cloudflare.com/" }
)
if ($DirectCheckUrl) {
    $checks += @{ Name="private DIRECT"; Url=$DirectCheckUrl }
}
foreach ($c in $checks) {
    $out = curl.exe -sS --ssl-no-revoke -o NUL --max-time 10 -x "http://127.0.0.1:$ProxyPort" `
        -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36" `
        -w "HTTP=%{http_code} tls=%{time_appconnect}s ttfb=%{time_starttransfer}s total=%{time_total}s" `
        $c.Url 2>&1
    Write-Output ("  {0,-18}: {1}" -f $c.Name, (Redact-Text ($out -join " ")))
}

if ($TailscaleVpsIp) {
    Write-Output "`n=== TAILSCALE FALLBACK CHECK (${TailscaleVpsNode}:${TailscaleVpsPort}) ==="
    $tp = tailscale ping -c 2 $TailscaleVpsNode 2>&1
    Write-Output ("  tailscale ping : " + (Redact-Text (($tp | Select-Object -Last 1) -join " ")))
    $tsOut = curl.exe -sS --ssl-no-revoke -o NUL --max-time 10 -x "socks5h://${TailscaleVpsIp}:${TailscaleVpsPort}" `
        -w "HTTP=%{http_code} tls=%{time_appconnect}s total=%{time_total}s" `
        "https://api.openai.com/v1/models" 2>&1
    Write-Output ("  socks5 openai  : " + (Redact-Text ($tsOut -join " ")))
}
