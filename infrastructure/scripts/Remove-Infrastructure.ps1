#Requires -Version 7.2
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'Medium')]
param([string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'), [switch]$DeleteStoredData)
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
$null = Assert-Identity $config
$state = Read-State $config

function Test-ResourcePresent {
    param([string]$Key, $Resource)
    if ($Key -eq 'service') {
        $r = Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $Resource.id) -NotFoundCodes @('ClusterNotFoundException')
        if ($null -ne $r) { Assert-DescribeFailures $r }
        return ($null -ne $r -and @($r.services | Where-Object { $_.status -ne 'INACTIVE' }).Count -gt 0)
    }
    if ($Key -eq 'cluster') {
        $r = Invoke-Aws $config @('ecs', 'describe-clusters', '--clusters', $Resource.id)
        Assert-DescribeFailures $r
        return (@($r.clusters | Where-Object { $_.status -eq 'ACTIVE' }).Count -gt 0)
    }
    try { Assert-Owned $config $state $Resource; return $true }
    catch {
        if ($_.Exception.Message -match '\((InvalidGroup.NotFound|RepositoryNotFoundException|ResourceNotFoundException|LoadBalancerNotFound|TargetGroupNotFound|ListenerNotFound)\)') { return $false }
        throw
    }
}

function Invoke-DeleteRetry {
    param([scriptblock]$Operation)
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        try { & $Operation; return }
        catch {
            if ($attempt -eq 19 -or $_.Exception.Message -notmatch '\((DependencyViolation|ResourceInUse|ResourceInUseException)\)') { throw }
            Write-Host 'Aguardando liberacao de dependencias de rede...'
            Start-Sleep -Seconds 15
        }
    }
}

function Wait-ServiceStopped {
    param([switch]$Deleted)
    for ($attempt = 0; $attempt -lt 40; $attempt++) {
        $r = Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $state.resources.service.id)
        if (@($r.services).Count -eq 0) {
            if ($Deleted -and @($r.failures | Where-Object { $_.reason -eq 'MISSING' }).Count -eq 1) { return }
            throw 'Resposta inesperada ao aguardar encerramento do servico.'
        }
        $service = $r.services[0]
        if ($Deleted) { if ($service.status -eq 'INACTIVE') { return } }
        elseif ($service.runningCount -eq 0 -and $service.pendingCount -eq 0) { return }
        Start-Sleep -Seconds 15
    }
    throw 'Servico ainda esta encerrando. Inventario preservado; execute a limpeza novamente.'
}

$order = @('service', 'listener', 'loadBalancer', 'targetGroup', 'taskSecurityGroup', 'albSecurityGroup', 'cluster')
if ($DeleteStoredData) { $order += @('repository', 'logGroup') }
foreach ($key in $order) {
    if (-not $state.resources.ContainsKey($key)) { continue }
    $resource = $state.resources[$key]
    $present = Test-ResourcePresent $key $resource
    if ($present) { Assert-Owned $config $state $resource }
    if (-not $PSCmdlet.ShouldProcess($resource.id, "Remover recurso do projeto ($key)")) { continue }
    if ($present) {
        switch ($key) {
            'service' {
                $null = Invoke-Aws $config @('ecs', 'update-service', '--cluster', $config.project, '--service', $resource.id, '--desired-count', '0')
                Wait-ServiceStopped
                $null = Invoke-Aws $config @('ecs', 'delete-service', '--cluster', $config.project, '--service', $resource.id)
                Wait-ServiceStopped -Deleted
            }
            'listener' { $null = Invoke-Aws $config @('elbv2', 'delete-listener', '--listener-arn', $resource.arn) }
            'loadBalancer' {
                $null = Invoke-Aws $config @('elbv2', 'delete-load-balancer', '--load-balancer-arn', $resource.arn)
                $null = Invoke-Aws $config @('elbv2', 'wait', 'load-balancers-deleted', '--load-balancer-arns', $resource.arn)
            }
            'targetGroup' { Invoke-DeleteRetry { $null = Invoke-Aws $config @('elbv2', 'delete-target-group', '--target-group-arn', $resource.arn) } }
            'taskSecurityGroup' { Invoke-DeleteRetry { $null = Invoke-Aws $config @('ec2', 'delete-security-group', '--group-id', $resource.id) } }
            'albSecurityGroup' { Invoke-DeleteRetry { $null = Invoke-Aws $config @('ec2', 'delete-security-group', '--group-id', $resource.id) } }
            'cluster' { $null = Invoke-Aws $config @('ecs', 'delete-cluster', '--cluster', $resource.id) }
            'repository' { $null = Invoke-Aws $config @('ecr', 'delete-repository', '--repository-name', $resource.id, '--force') }
            'logGroup' { $null = Invoke-Aws $config @('logs', 'delete-log-group', '--log-group-name', $resource.id) }
        }
    }
    $state.resources.Remove($key)
    Save-State $config $state
}
foreach ($arn in @($state.taskDefinitions)) {
    $definition = Invoke-Aws $config @('ecs', 'describe-task-definition', '--task-definition', $arn)
    Assert-Owned $config $state @{kind = 'ecs'; id = $arn; arn = $arn}
    if ($PSCmdlet.ShouldProcess($arn, 'Desregistrar revisao da task definition do projeto')) {
        if ($definition.taskDefinition.status -eq 'ACTIVE') { $null = Invoke-Aws $config @('ecs', 'deregister-task-definition', '--task-definition', $arn) }
        $state.taskDefinitions = @($state.taskDefinitions | Where-Object { $_ -ne $arn })
        Save-State $config $state
    }
}
if (-not $WhatIfPreference) {
    $report = @{timestampUtc = [DateTimeOffset]::UtcNow.ToString('o'); accountId = $config.accountId; region = $config.region; remainingResources = $state.resources; retainedData = -not $DeleteStoredData}
    Write-Json (Join-Path $script:InfraRoot ('evidence/cleanup-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '.json')) $report
    if ($state.resources.Count) { Write-Warning 'Recursos preservados no inventario podem ter custo de armazenamento. Exporte as evidencias e use -DeleteStoredData quando a equipe decidir excluir imagens e logs.' }
    else { Write-Host 'Recursos do inventario removidos. Confira tambem o console e o consumo da conta; o inventario nao cobre criacoes manuais.' }
}
