$ErrorActionPreference = 'Stop'
Push-Location (Join-Path $PSScriptRoot 'sub2api/frontend')
try {
    if (-not (Test-Path 'node_modules/.bin/vite.cmd')) {
        npx --yes pnpm@9.15.9 install --frozen-lockfile
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    }
    npx --yes pnpm@9.15.9 run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
} finally {
    Pop-Location
}
