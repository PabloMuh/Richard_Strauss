#Requires -Version 7.2
[CmdletBinding()]
param([string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'))
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
Assert-DeploymentConfig $config
Assert-SpendingWindow $config
$null = Assert-Identity $config
Assert-PublicNetwork $config
$role = Invoke-Aws $config @('iam', 'get-role', '--role-name', ($config.executionRoleArn -split '/')[-1])
if ($role.Role.Arn -ne $config.executionRoleArn) { throw 'Execution role nao corresponde a configurada.' }
$state = Read-State $config -Create
Assert-InfrastructureShape $config $state
$tags = Get-ResourceTags $config $state
$tagJson = ConvertTo-Json -InputObject $tags -Compress
$prefix = $config.project

function Test-Reuse {
    param([string]$Key, [string]$FoundId)
    if ($state.resources.ContainsKey($Key)) {
        if ($state.resources[$Key].id -ne $FoundId) { throw "Recurso $Key diverge do inventario. Revise antes de continuar." }
        Assert-Owned $config $state $state.resources[$Key]
        return $true
    }
    if ($FoundId) { throw "Colisao com recurso existente: $Key ($FoundId). Nao sera adotado nem alterado. Escolha outro project ou restaure seu inventario." }
    return $false
}

$existing = Invoke-Aws $config @('ecr', 'describe-repositories', '--repository-names', $prefix) -NotFoundCodes @('RepositoryNotFoundException')
$found = if ($existing) { $existing.repositories[0].repositoryName } else { '' }
if (-not (Test-Reuse 'repository' $found)) {
    $ecrTags = @($tags | ForEach-Object { @{Key = $_.key; Value = $_.value} })
    $ecrTagJson = ConvertTo-Json -InputObject $ecrTags -Compress
    $r = (Invoke-Aws $config @('ecr', 'create-repository', '--repository-name', $prefix, '--image-tag-mutability', 'IMMUTABLE', '--tags', $ecrTagJson)).repository
    Add-Resource $config $state 'repository' 'ecr' $r.repositoryName $r.repositoryArn
}

$logName = "/ecs/$prefix"
$logs = (Invoke-Aws $config @('logs', 'describe-log-groups', '--log-group-name-prefix', $logName)).logGroups
$foundLog = @($logs | Where-Object { $_.logGroupName -eq $logName })
$found = if ($foundLog.Count) { $foundLog[0].logGroupName } else { '' }
if (-not (Test-Reuse 'logGroup' $found)) {
    $tagMap = @{}; foreach ($tag in $tags) { $tagMap[$tag.key] = $tag.value }
    $null = Invoke-Aws $config @('logs', 'create-log-group', '--log-group-name', $logName, '--tags', ($tagMap | ConvertTo-Json -Compress))
    Add-Resource $config $state 'logGroup' 'logs' $logName "arn:aws:logs:$($config.region):$($config.accountId):log-group:$logName"
}
$null = Invoke-Aws $config @('logs', 'put-retention-policy', '--log-group-name', $logName, '--retention-in-days', '7')

$clusters = Invoke-Aws $config @('ecs', 'describe-clusters', '--clusters', $prefix)
Assert-DescribeFailures $clusters
$active = @($clusters.clusters | Where-Object { $_.status -eq 'ACTIVE' })
$found = if ($active.Count) { $active[0].clusterName } else { '' }
if (-not (Test-Reuse 'cluster' $found)) {
    $cluster = (Invoke-Aws $config @('ecs', 'create-cluster', '--cluster-name', $prefix, '--tags', $tagJson, '--settings', 'name=containerInsights,value=disabled')).cluster
    Add-Resource $config $state 'cluster' 'ecs' $cluster.clusterName $cluster.clusterArn
}

function Ensure-Group {
    param([string]$Key, [string]$Name)
    $groups = (Invoke-Aws $config @('ec2', 'describe-security-groups', '--filters', "Name=group-name,Values=$Name", "Name=vpc-id,Values=$($config.vpcId)")).SecurityGroups
    $found = if (@($groups).Count) { $groups[0].GroupId } else { '' }
    if (-not (Test-Reuse $Key $found)) {
        $ec2Tags = @($tags | ForEach-Object { @{Key = $_.key; Value = $_.value} })
        $request = @{GroupName = $Name; Description = "Projeto $prefix"; VpcId = $config.vpcId; TagSpecifications = @(@{ResourceType = 'security-group'; Tags = $ec2Tags})}
        $group = Invoke-Aws $config @('ec2', 'create-security-group', '--cli-input-json', (Write-Request "create-$Key" $request))
        Add-Resource $config $state $Key 'ec2' $group.GroupId ''
    }
}

Ensure-Group 'taskSecurityGroup' "$prefix-tasks"
if ($config.useAlb) { Ensure-Group 'albSecurityGroup' "$prefix-alb" }

# Retomar uma criacao parcial e seguro; somente a regra exatamente duplicada e ignorada.
$ingressKey = if ($config.useAlb) { 'albSecurityGroup' } else { 'taskSecurityGroup' }
$ingressPort = if ($config.useAlb) { 80 } else { $config.containerPort }
$permission = @{IpProtocol = 'tcp'; FromPort = $ingressPort; ToPort = $ingressPort; IpRanges = @($config.allowedCidrs | ForEach-Object { @{CidrIp = $_; Description = 'Participante do trabalho'} })}
foreach ($range in $permission.IpRanges) {
    $single = @{IpProtocol = 'tcp'; FromPort = $ingressPort; ToPort = $ingressPort; IpRanges = @($range)}
    $null = Invoke-Aws $config @('ec2', 'authorize-security-group-ingress', '--group-id', $state.resources[$ingressKey].id, '--ip-permissions', (ConvertTo-Json -InputObject @($single) -Depth 10 -Compress)) -NotFoundCodes @('InvalidPermission.Duplicate')
}
if ($config.useAlb) {
    $rule = @{IpProtocol = 'tcp'; FromPort = $config.containerPort; ToPort = $config.containerPort; UserIdGroupPairs = @(@{GroupId = $state.resources.albSecurityGroup.id})}
    $null = Invoke-Aws $config @('ec2', 'authorize-security-group-ingress', '--group-id', $state.resources.taskSecurityGroup.id, '--ip-permissions', (ConvertTo-Json -InputObject @($rule) -Depth 10 -Compress)) -NotFoundCodes @('InvalidPermission.Duplicate')
    $lb = Invoke-Aws $config @('elbv2', 'describe-load-balancers', '--names', "$prefix-alb") -NotFoundCodes @('LoadBalancerNotFound')
    $found = if ($lb) { $lb.LoadBalancers[0].LoadBalancerArn } else { '' }
    if (-not (Test-Reuse 'loadBalancer' $found)) {
        $request = @{Name = "$prefix-alb"; Subnets = @($config.subnetIds); SecurityGroups = @($state.resources.albSecurityGroup.id); Scheme = 'internet-facing'; Type = 'application'; IpAddressType = 'ipv4'; Tags = @($tags | ForEach-Object { @{Key = $_.key; Value = $_.value} })}
        $lb = Invoke-Aws $config @('elbv2', 'create-load-balancer', '--cli-input-json', (Write-Request 'create-alb' $request))
        $arn = $lb.LoadBalancers[0].LoadBalancerArn
        Add-Resource $config $state 'loadBalancer' 'elbv2' $arn $arn
    }
    $tg = Invoke-Aws $config @('elbv2', 'describe-target-groups', '--names', "$prefix-api") -NotFoundCodes @('TargetGroupNotFound')
    $found = if ($tg) { $tg.TargetGroups[0].TargetGroupArn } else { '' }
    if (-not (Test-Reuse 'targetGroup' $found)) {
        $request = @{Name = "$prefix-api"; Protocol = 'HTTP'; Port = $config.containerPort; VpcId = $config.vpcId; TargetType = 'ip'; HealthCheckProtocol = 'HTTP'; HealthCheckPath = '/health'; Matcher = @{HttpCode = '200'}; Tags = @($tags | ForEach-Object { @{Key = $_.key; Value = $_.value} })}
        $tg = Invoke-Aws $config @('elbv2', 'create-target-group', '--cli-input-json', (Write-Request 'create-target-group' $request))
        $arn = $tg.TargetGroups[0].TargetGroupArn
        Add-Resource $config $state 'targetGroup' 'elbv2' $arn $arn
    }
    # Health check a cada 10 s (2 acertos ou 2 falhas) e drenagem de 30 s: com os padroes (30 s, 5 acertos,
    # 300 s), uma task nova levaria 150 s para receber trafego e uma encerrada drenaria por 5 min, o que
    # distorce os tempos de scale-out, scale-in e substituicao medidos nos experimentos.
    $null = Invoke-Aws $config @('elbv2', 'modify-target-group', '--target-group-arn', $state.resources.targetGroup.arn, '--health-check-interval-seconds', '10', '--health-check-timeout-seconds', '5', '--healthy-threshold-count', '2', '--unhealthy-threshold-count', '2')
    $null = Invoke-Aws $config @('elbv2', 'modify-target-group-attributes', '--target-group-arn', $state.resources.targetGroup.arn, '--attributes', 'Key=deregistration_delay.timeout_seconds,Value=30')
    $listeners = (Invoke-Aws $config @('elbv2', 'describe-listeners', '--load-balancer-arn', $state.resources.loadBalancer.arn)).Listeners
    $httpListeners = @($listeners | Where-Object { $_.Port -eq 80 })
    $found = if ($httpListeners.Count) { $httpListeners[0].ListenerArn } else { '' }
    if (-not (Test-Reuse 'listener' $found)) {
        $request = @{LoadBalancerArn = $state.resources.loadBalancer.arn; Protocol = 'HTTP'; Port = 80; DefaultActions = @(@{Type = 'forward'; TargetGroupArn = $state.resources.targetGroup.arn}); Tags = @($tags | ForEach-Object { @{Key = $_.key; Value = $_.value} })}
        $listener = Invoke-Aws $config @('elbv2', 'create-listener', '--cli-input-json', (Write-Request 'create-listener' $request))
        $arn = $listener.Listeners[0].ListenerArn
        Add-Resource $config $state 'listener' 'elbv2' $arn $arn
    }
}
Write-Host "Infraestrutura registrada em $(Get-StatePath $config). Proximo passo: Publish-Image.ps1 quando a API estiver disponivel."
