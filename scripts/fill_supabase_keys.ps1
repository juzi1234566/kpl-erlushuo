# 一次性把 Supabase 三个值写进 pipeline/.env 和 web/.env.local
# 用法（在本机 PowerShell）：
#   .\scripts\fill_supabase_keys.ps1 -Url "https://xxxx.supabase.co" -AnonKey "eyJ..." -ServiceRoleKey "eyJ..."

param(
  [Parameter(Mandatory = $true)][string]$Url,
  [Parameter(Mandatory = $true)][string]$AnonKey,
  [Parameter(Mandatory = $true)][string]$ServiceRoleKey
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$pipeEnv = Join-Path $root 'pipeline\.env'
$webEnv = Join-Path $root 'web\.env.local'

function Set-EnvFileKey([string]$Path, [string]$Key, [string]$Value) {
  $lines = @()
  if (Test-Path $Path) {
    $lines = Get-Content -LiteralPath $Path
  }
  $found = $false
  $out = foreach ($line in $lines) {
    if ($line -match "^$([regex]::Escape($Key))=") {
      $found = $true
      "$Key=$Value"
    } else {
      $line
    }
  }
  if (-not $found) { $out = @($out) + "$Key=$Value" }
  Set-Content -LiteralPath $Path -Value $out -Encoding utf8
}

if (-not (Test-Path $pipeEnv)) {
  @"
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
RAW_DATA_DIR=./data/raw
"@ | Set-Content -LiteralPath $pipeEnv -Encoding utf8
}

Set-EnvFileKey $pipeEnv 'SUPABASE_URL' $Url
Set-EnvFileKey $pipeEnv 'SUPABASE_SERVICE_ROLE_KEY' $ServiceRoleKey

@"
NEXT_PUBLIC_SUPABASE_URL=$Url
NEXT_PUBLIC_SUPABASE_ANON_KEY=$AnonKey
NEXT_PUBLIC_SITE_URL=http://localhost:3000
"@ | Set-Content -LiteralPath $webEnv -Encoding utf8

Write-Host "已写入:"
Write-Host "  $pipeEnv"
Write-Host "  $webEnv"
Write-Host "请运行: cd pipeline; .\.venv\Scripts\python.exe -m scripts.check_env"
