param(
    [Parameter(Mandatory = $true)]
    [string]$Kubeconfig
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Kubeconfig)) { throw 'Kubeconfig file not found.' }
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
kubectl --kubeconfig $Kubeconfig apply -f (Join-Path $PSScriptRoot 'namespace.yaml')
if ($LASTEXITCODE -ne 0) { throw 'Namespace creation failed.' }
kubectl --kubeconfig $Kubeconfig -n warpgate get secret warpgate-secrets -o name 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    function New-ClusterSecret {
        return [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLowerInvariant()
    }
    $adminPassword = 'WarpGate-' + (New-ClusterSecret).Substring(0, 24)
    $values = @{
        POSTGRES_PASSWORD = New-ClusterSecret
        REDIS_PASSWORD = New-ClusterSecret
        JWT_SECRET = New-ClusterSecret
        TOTP_ENCRYPTION_KEY = New-ClusterSecret
        ADMIN_EMAIL = 'admin@warpgate.local'
        ADMIN_PASSWORD = $adminPassword
    }
    $secret = @{
        apiVersion = 'v1'; kind = 'Secret'; type = 'Opaque'
        metadata = @{ name = 'warpgate-secrets'; namespace = 'warpgate' }
        stringData = $values
    }
    $secret | ConvertTo-Json -Depth 5 | kubectl --kubeconfig $Kubeconfig create -f -
    if ($LASTEXITCODE -ne 0) { throw 'Secret creation failed.' }
    $localDirectory = Join-Path $repoRoot '.local'
    New-Item -ItemType Directory -Force -Path $localDirectory | Out-Null
    [IO.File]::WriteAllLines((Join-Path $localDirectory 'cluster-admin.txt'), @(
        'Namespace: warpgate'
        'Email: admin@warpgate.local'
        ('Password: ' + $adminPassword)
    ))
}
kubectl --kubeconfig $Kubeconfig apply -k $PSScriptRoot
if ($LASTEXITCODE -ne 0) { throw 'Manifest application failed.' }
Write-Host 'Resources applied. Credentials stay in .local/cluster-admin.txt.'
