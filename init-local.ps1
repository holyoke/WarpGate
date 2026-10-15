$ErrorActionPreference = 'Stop'
$configPath = Join-Path $PSScriptRoot '.env'
if (Test-Path -LiteralPath $configPath) { return }
function New-LocalSecret {
    $bytes = New-Object byte[] 32
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}
$adminPassword = 'WarpGate-' + (New-LocalSecret).Substring(0, 20)
[IO.File]::WriteAllLines($configPath, @(
    'COMPOSE_PROJECT_NAME=warp-sub2api'
    'BIND_HOST=127.0.0.1'
    'SERVER_PORT=8080'
    'TZ=Asia/Shanghai'
    ('POSTGRES_PASSWORD=' + (New-LocalSecret))
    ('REDIS_PASSWORD=' + (New-LocalSecret))
    ('JWT_SECRET=' + (New-LocalSecret))
    ('TOTP_ENCRYPTION_KEY=' + (New-LocalSecret))
    'ADMIN_EMAIL=admin@warp.local'
    ('ADMIN_PASSWORD=' + $adminPassword)
))
$localDirectory = Join-Path $PSScriptRoot '.local'
New-Item -ItemType Directory -Force -Path $localDirectory | Out-Null
[IO.File]::WriteAllLines((Join-Path $localDirectory 'admin-login.txt'), @(
    'URL: http://localhost:8080'
    'Email: admin@warp.local'
    ('Password: ' + $adminPassword)
))
Write-Host 'Generated local configuration. Credentials: .local/admin-login.txt'
