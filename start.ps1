$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $initializeBrand = -not (Test-Path '.env')
    & (Join-Path $PSScriptRoot 'init-local.ps1')
    if (-not (Test-Path 'sub2api/backend/internal/web/dist/index.html')) {
        & (Join-Path $PSScriptRoot 'build-ui.ps1')
    }
    docker compose up -d --wait --wait-timeout 240
    if ($LASTEXITCODE -ne 0) { throw 'WarpGate startup failed. Run docker compose logs --tail 100.' }
    if ($initializeBrand) {
        $localConfig = @{}
        Get-Content '.env' | ForEach-Object {
            if ($_ -match '^([^#=]+)=(.*)$') { $localConfig[$matches[1]] = $matches[2] }
        }
        $loginBody = @{ email = $localConfig.ADMIN_EMAIL; password = $localConfig.ADMIN_PASSWORD } | ConvertTo-Json
        $session = (Invoke-RestMethod 'http://localhost:8080/api/v1/auth/login' -Method Post -ContentType 'application/json' -Body $loginBody).data
        $headers = @{ Authorization = ('Bearer ' + $session.access_token); 'X-Admin-UI-Request' = 'true' }
        $branding = @{ site_name = 'WarpGate'; site_subtitle = '连接模型，让灵感即刻运行'; site_logo = '/logo.svg' } | ConvertTo-Json
        Invoke-RestMethod 'http://localhost:8080/api/v1/admin/settings' -Method Put -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $branding | Out-Null
    }
    Write-Host 'WarpGate: http://localhost:8080'
    Write-Host 'Local administrator credentials: ADMIN_EMAIL / ADMIN_PASSWORD in .env'
} finally {
    Pop-Location
}
