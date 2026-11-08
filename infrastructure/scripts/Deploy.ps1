#Requires -Version 7.2
[CmdletBinding()]
param([string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'), [ValidateRange(1, 30)][int]$TimeoutMinutes = 10)
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
Assert-DeploymentConfig $config
Assert-SpendingWindow $config
if ($config.imageTag -eq 'latest' -or $config.imageTag -cnotmatch '^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$') { throw 'Informe imageTag fixa publicada no ECR.' }
$null = Assert-Identity $config
Assert-PublicNetwork $config
$state = Read-State $config
Assert-InfrastructureShape $config $state
$required = @('repository', 'cluster', 'logGroup', 'taskSecurityGroup')
if ($config.useAlb) { $required += @('loadBalancer', 'targetGroup', 'listener', 'albSecurityGroup') }
foreach ($key in $required) {
    if (-not $state.resources.ContainsKey($key)) { throw "Provisionamento incompleto: $key. Execute Provision.ps1." }
    Assert-Owned $config $state $state.resources[$key]
}
$image = (Invoke-Aws $config @('ecr', 'describe-images', '--repository-name', $config.project, '--image-ids', "imageTag=$($config.imageTag)")).imageDetails[0]
$imageUri = "$($config.accountId).dkr.ecr.$($config.region).amazonaws.com/$($config.project)@$($image.imageDigest)"
$targetGroup = if ($config.useAlb) { $state.resources.targetGroup.arn } else { '' }
$spec = New-DeploymentSpec $config $imageUri $state.resources.taskSecurityGroup.id $targetGroup $state.deploymentId
$serviceName = "$($config.project)-api"
$description = Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $serviceName)
Assert-DescribeFailures $description
$services = @($description.services | Where-Object { $_.status -ne 'INACTIVE' })
if ($services.Count -gt 0) {
    if (-not $state.resources.ContainsKey('service') -or $state.resources.service.arn -ne $services[0].serviceArn) { throw 'Servico existente fora do inventario. Nenhuma alteracao executada.' }
    Assert-Owned $config $state $state.resources.service
} elseif ($state.resources.ContainsKey('service')) { throw 'Servico do inventario foi removido externamente. Revise o inventario.' }
Write-Json (Join-Path $script:InfraRoot 'generated/task-definition.json') $spec.task
$registered = Invoke-Aws $config @('ecs', 'register-task-definition', '--cli-input-json', (Write-Request 'task-definition' $spec.task))
$revision = $registered.taskDefinition.taskDefinitionArn
$state.taskDefinitions += $revision
$state.image = @{tag = $config.imageTag; digest = $image.imageDigest; uri = $imageUri; timestampUtc = [DateTimeOffset]::UtcNow.ToString('o')}
Save-State $config $state
$spec.service.taskDefinition = $revision
if ($services.Count -eq 0) {
    $response = Invoke-Aws $config @('ecs', 'create-service', '--cli-input-json', (Write-Request 'service' $spec.service))
    Add-Resource $config $state 'service' 'ecs' $serviceName $response.service.serviceArn
} else {
    $update = @{cluster = $config.project; service = $serviceName; taskDefinition = $revision; desiredCount = $config.desiredCount; deploymentConfiguration = $spec.service.deploymentConfiguration}
    $null = Invoke-Aws $config @('ecs', 'update-service', '--cli-input-json', (Write-Request 'update-service' $update))
}
$deadline = [DateTimeOffset]::UtcNow.AddMinutes($TimeoutMinutes)
do {
    $service = (Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $serviceName)).services[0]
    $primary = @($service.deployments | Where-Object { $_.status -eq 'PRIMARY' })
    if ($primary.Count -and $primary[0].taskDefinition -ne $revision) { throw 'Deploy revertido pelo ECS. Consulte eventos e logs com Get-Status.ps1.' }
    if ($primary.Count -and $primary[0].ContainsKey('rolloutState') -and $primary[0].rolloutState -eq 'FAILED') { throw 'Deploy falhou no ECS. Consulte Get-Status.ps1 e preserve as evidencias.' }
    if ($service.taskDefinition -eq $revision -and $service.runningCount -eq $config.desiredCount -and $service.pendingCount -eq 0 -and @($service.deployments).Count -eq 1 -and $primary[0].rolloutState -eq 'COMPLETED') {
        $snapshot = Get-DeploymentSnapshot $config $state
        Write-Json (Join-Path $script:InfraRoot ('evidence/deploy-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '.json')) $snapshot
        Write-Host "Deploy estavel: $revision. Execute Test-Deployment.ps1 para validar HTTP e logs."
        return
    }
    Write-Host "Aguardando ECS: desired=$($service.desiredCount), running=$($service.runningCount), pending=$($service.pendingCount)"
    Start-Sleep -Seconds 15
} while ([DateTimeOffset]::UtcNow -lt $deadline)
throw 'Tempo de espera excedido. Recursos continuam ativos; consulte Get-Status.ps1 e encerre a sessao conforme o roteiro.'
