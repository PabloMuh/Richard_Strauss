#Requires -Version 7.2
[CmdletBinding()]
param([string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'))
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
$null = Assert-Identity $config
$state = Read-State $config
$snapshot = Get-DeploymentSnapshot $config $state
$path = Join-Path $script:InfraRoot ('evidence/status-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '.json')
Write-Json $path $snapshot
if ($snapshot.service) { Write-Host "desired=$($snapshot.service.desiredCount), running=$($snapshot.service.runningCount), pending=$($snapshot.service.pendingCount)" }
foreach ($endpoint in $snapshot.endpoints) { Write-Host "Endpoint: $endpoint" }
Write-Host "Evidencias (eventos ECS, tasks, metricas e streams de logs): $path"
