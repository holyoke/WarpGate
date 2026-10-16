# All arguments are forwarded unchanged; requires Python 3.9+.
$ErrorActionPreference = 'Stop'
if (Get-Command python -ErrorAction SilentlyContinue) {
    & python (Join-Path $PSScriptRoot 'install/install.py') @args
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 (Join-Path $PSScriptRoot 'install/install.py') @args
} else {
    throw 'Install Python 3.9+ and add it to PATH, then retry.'
}
exit $LASTEXITCODE
