#Requires -Version 7.2
[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'),
    [Parameter(Mandatory)][string]$ImageUri,
    [Parameter(Mandatory)][string]$SecurityGroupId,
    [string]$TargetGroupArn = '',
    [string]$OutputDirectory = (Join-Path $PSScriptRoot '../generated/preview')
)
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
$spec = New-DeploymentSpec $config $ImageUri $SecurityGroupId $TargetGroupArn
Write-Json (Join-Path $OutputDirectory 'task-definition.json') $spec.task
Write-Json (Join-Path $OutputDirectory 'service.json') $spec.service
Write-Host "Preview local em $OutputDirectory. Nenhuma chamada AWS executada; o deploy substitui a referencia pela revisao registrada."
