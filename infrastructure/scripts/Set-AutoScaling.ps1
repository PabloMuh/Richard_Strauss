#Requires -Version 7.2
<#
.SYNOPSIS
Configura o Auto Scaling do servico ECS (pessoas 2 e 3): target tracking pela CPU media do servico.

.DESCRIPTION
Registra o servico como scalable target do Application Auto Scaling (com tags de propriedade) e
cria ou atualiza a politica de target tracking ECSServiceAverageCPUUtilization. Os valores padrao
seguem o plano: 1 a 3 tasks, CPU-alvo de 60%, cooldown de 60 s para scale-out e 180 s para scale-in.
Executar de novo atualiza os limites e a politica. Para remover: Remove-AutoScaling.ps1.
#>
[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'),
    [int]$MinTasks = 1,
    [int]$MaxTasks = 3,
    [double]$TargetCpu = 60,
    [int]$ScaleOutCooldown = 60,
    [int]$ScaleInCooldown = 180
)
. "$PSScriptRoot/Common.ps1"
Assert-AutoScalingParameters $MinTasks $MaxTasks $TargetCpu $ScaleOutCooldown $ScaleInCooldown
$config = Read-Config $ConfigPath
Assert-DeploymentConfig $config
Assert-SpendingWindow $config
$null = Assert-Identity $config
$state = Read-State $config
if (-not $state.resources.ContainsKey('service')) { throw 'Servico ausente no inventario. Execute Deploy.ps1 antes de configurar o Auto Scaling.' }
Assert-Owned $config $state $state.resources.service
if (-not $config.useAlb) { Write-Warning 'Sem ALB (useAlb=false), as tasks criadas pelo Auto Scaling nao recebem trafego por um endereco unico; os experimentos B e C exigem ALB.' }

$resourceId = Get-ScalableResourceId $config
$existing = @((Invoke-Aws $config @('application-autoscaling', 'describe-scalable-targets', '--service-namespace', 'ecs', '--resource-ids', $resourceId)).ScalableTargets)
if ($state.resources.ContainsKey('scalableTarget')) {
    if (-not $existing.Count) { throw 'O scalable target do inventario foi removido fora dos scripts. Execute Remove-AutoScaling.ps1 para limpar o inventario.' }
    Assert-Owned $config $state $state.resources.scalableTarget
    $null = Invoke-Aws $config @('application-autoscaling', 'register-scalable-target', '--cli-input-json', (Write-Request 'register-scalable-target' (New-ScalableTargetRequest $config $state $MinTasks $MaxTasks)))
} else {
    if ($existing.Count) { throw "Colisao com scalable target existente ($resourceId) fora do inventario. Nao sera adotado nem alterado." }
    $registered = Invoke-Aws $config @('application-autoscaling', 'register-scalable-target', '--cli-input-json', (Write-Request 'register-scalable-target' (New-ScalableTargetRequest $config $state $MinTasks $MaxTasks -WithTags)))
    $arn = if ($registered.ContainsKey('ScalableTargetARN')) { $registered.ScalableTargetARN } else {
        @((Invoke-Aws $config @('application-autoscaling', 'describe-scalable-targets', '--service-namespace', 'ecs', '--resource-ids', $resourceId)).ScalableTargets)[0].ScalableTargetARN
    }
    Add-Resource $config $state 'scalableTarget' 'aas' $resourceId $arn
}
$policy = Invoke-Aws $config @('application-autoscaling', 'put-scaling-policy', '--cli-input-json', (Write-Request 'put-scaling-policy' (New-ScalingPolicyRequest $config $TargetCpu $ScaleOutCooldown $ScaleInCooldown)))
$state.autoScaling = [ordered]@{
    minTasks = $MinTasks; maxTasks = $MaxTasks; targetCpu = $TargetCpu; scaleOutCooldown = $ScaleOutCooldown; scaleInCooldown = $ScaleInCooldown
    policyName = "$($config.project)-cpu"; policyArn = $policy.PolicyARN
    alarms = @(@($policy.Alarms) | ForEach-Object { $_.AlarmName }); timestampUtc = [DateTimeOffset]::UtcNow.ToString('o')
}
Save-State $config $state
Write-Json (Join-Path $script:InfraRoot ('evidence/autoscaling-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '.json')) $state.autoScaling
Write-Host "Auto Scaling ativo: $MinTasks a $MaxTasks tasks, CPU-alvo $TargetCpu%, cooldown $ScaleOutCooldown s (scale-out) / $ScaleInCooldown s (scale-in)."
Write-Host 'Lembre: o maximo de tasks e o ALB entram na estimativa de custo da sessao. Remover: Remove-AutoScaling.ps1.'
