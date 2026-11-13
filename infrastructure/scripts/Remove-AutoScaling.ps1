#Requires -Version 7.2
<#
.SYNOPSIS
Remove o Auto Scaling do servico e fixa a quantidade de tasks.

.DESCRIPTION
Desregistra o scalable target do inventario (o Application Auto Scaling apaga junto a politica e os
alarmes do target tracking) e ajusta o servico para -DesiredCount tasks (padrao: desiredCount da
configuracao), aguardando estabilizar. Use -DesiredCount 2 antes do experimento D.
#>
[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'),
    [int]$DesiredCount = 0,
    [ValidateRange(1, 30)][int]$TimeoutMinutes = 10
)
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
Assert-DeploymentConfig $config
$null = Assert-Identity $config
$state = Read-State $config
if ($DesiredCount -eq 0) { $DesiredCount = [int]$config.desiredCount }
if ($DesiredCount -notin @(1, 2)) { throw 'DesiredCount deve ser 1 ou 2 sem Auto Scaling.' }

if ($state.resources.ContainsKey('scalableTarget')) {
    $target = $state.resources.scalableTarget
    $exists = @((Invoke-Aws $config @('application-autoscaling', 'describe-scalable-targets', '--service-namespace', 'ecs', '--resource-ids', $target.id)).ScalableTargets).Count -gt 0
    if ($exists) {
        Assert-Owned $config $state $target
        $null = Invoke-Aws $config @('application-autoscaling', 'deregister-scalable-target', '--service-namespace', 'ecs', '--scalable-dimension', 'ecs:service:DesiredCount', '--resource-id', $target.id)
    }
    $state.resources.Remove('scalableTarget')
    if ($state.ContainsKey('autoScaling')) { $state.Remove('autoScaling') }
    Save-State $config $state
    Write-Host 'Auto Scaling removido (a politica e os alarmes do target tracking sao apagados com o scalable target).'
} else {
    Write-Host 'Nenhum Auto Scaling no inventario.'
}

if (-not $state.resources.ContainsKey('service')) { Write-Host 'Nenhum servico no inventario; nada a ajustar.'; return }
Assert-Owned $config $state $state.resources.service
$serviceName = $state.resources.service.id
$null = Invoke-Aws $config @('ecs', 'update-service', '--cluster', $config.project, '--service', $serviceName, '--desired-count', [string]$DesiredCount)
$deadline = [DateTimeOffset]::UtcNow.AddMinutes($TimeoutMinutes)
do {
    $service = (Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $serviceName)).services[0]
    if ($service.desiredCount -eq $DesiredCount -and $service.runningCount -eq $DesiredCount -and $service.pendingCount -eq 0) {
        Write-Host "Servico estavel com $DesiredCount task(s)."
        return
    }
    Write-Host "Aguardando ECS: desired=$($service.desiredCount), running=$($service.runningCount), pending=$($service.pendingCount)"
    Start-Sleep -Seconds 15
} while ([DateTimeOffset]::UtcNow -lt $deadline)
throw "O servico nao estabilizou em $TimeoutMinutes min. Consulte Get-Status.ps1."
