#Requires -Version 7.2
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script:InfraRoot = Split-Path $PSScriptRoot -Parent

function Write-Json {
    param([string]$Path, $Value)
    $full = [IO.Path]::GetFullPath($Path)
    [IO.Directory]::CreateDirectory((Split-Path $full -Parent)) | Out-Null
    $temporary = "$full.tmp"
    [IO.File]::WriteAllText($temporary, (ConvertTo-Json -InputObject $Value -Depth 100), [Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $temporary -Destination $full -Force
}

function Read-Config {
    param([string]$Path = (Join-Path $script:InfraRoot 'config.local.json'))
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Configuracao ausente: $Path. Copie infrastructure/config.example.json para config.local.json e preencha os dados da conta do trabalho."
    }
    $config = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -AsHashtable
    $example = Get-Content -LiteralPath (Join-Path $script:InfraRoot 'config.example.json') -Raw | ConvertFrom-Json -AsHashtable
    foreach ($key in $example.Keys) {
        if (-not $config.ContainsKey($key)) { throw "Campo obrigatorio ausente: $key" }
    }
    if ($config.project -cnotmatch '^[a-z][a-z0-9-]{2,23}$') { throw 'project deve ter de 3 a 24 caracteres: letras minusculas, numeros e hifens.' }
    if ($config.containerPort -isnot [long] -and $config.containerPort -isnot [int]) { throw 'containerPort deve ser inteiro.' }
    if ($config.containerPort -lt 1 -or $config.containerPort -gt 65535) { throw 'Porta invalida.' }
    if ($config.desiredCount -notin @(1, 2)) { throw 'Nesta etapa, desiredCount deve ser 1 ou 2.' }
    if ([string]$config.cpu -ne '256' -or [string]$config.memory -ne '512') { throw 'Esta entrega usa cpu=256 e memory=512.' }
    if ($config.useAlb -isnot [bool]) { throw 'useAlb deve ser booleano.' }
    if ($config.logRetentionDays -ne 7) { throw 'Esta entrega usa retencao de logs de 7 dias.' }
    foreach ($item in $config.environment) {
        if ($item.name -notmatch '^[A-Za-z_][A-Za-z0-9_]*$' -or $item.value -isnot [string]) { throw 'Variavel de ambiente invalida: use name e value textual.' }
    }
    if (@($config.environment | Where-Object { $_.name -eq 'PORT' -and $_.value -ne [string]$config.containerPort }).Count) { throw 'environment.PORT deve ser omitido ou igual a containerPort; o deploy define PORT a partir de containerPort.' }
    return $config
}

function Assert-AccountConfig {
    param($Config, [switch]$Discovery)
    if ([string]::IsNullOrWhiteSpace($Config.profile)) { throw 'Informe explicitamente o profile AWS do trabalho.' }
    if ($Config.region -notmatch '^[a-z]{2}(-[a-z0-9]+)+-\d$') { throw 'Informe a regiao AWS autorizada.' }
    if (-not $Discovery -and $Config.accountId -notmatch '^\d{12}$') { throw 'Informe accountId com 12 digitos para impedir uso da conta errada.' }
}

function Assert-DeploymentConfig {
    param($Config)
    Assert-AccountConfig $Config
    if ($Config.vpcId -notmatch '^vpc-[a-f0-9]+$') { throw 'Informe vpcId existente.' }
    if (@($Config.subnetIds).Count -lt 1) { throw 'Informe ao menos uma subnet publica existente.' }
    foreach ($subnet in $Config.subnetIds) { if ($subnet -notmatch '^subnet-[a-f0-9]+$') { throw "Subnet invalida: $subnet" } }
    if ($Config.executionRoleArn -notmatch "^arn:aws:iam::$($Config.accountId):role/.+$") { throw 'executionRoleArn deve pertencer a conta do trabalho.' }
    if (@($Config.allowedCidrs).Count -eq 0) { throw 'Informe os IPv4 /32 dos participantes em allowedCidrs.' }
    foreach ($cidr in $Config.allowedCidrs) {
        $ip = $null
        if ($cidr -notmatch '^(.+)/32$' -or -not [Net.IPAddress]::TryParse($Matches[1], [ref]$ip) -or $ip.AddressFamily -ne 'InterNetwork') { throw "Use somente IPv4 /32 em allowedCidrs: $cidr" }
    }
    if ($Config.useAlb -and @($Config.subnetIds | Select-Object -Unique).Count -lt 2) { throw 'ALB requer subnets em pelo menos duas zonas.' }
}

function Assert-SpendingWindow {
    param($Config)
    foreach ($key in @('approvedBy', 'reference', 'maxUsd', 'estimatedSessionUsd', 'sessionEndsAtUtc')) {
        if (-not $Config.budget.ContainsKey($key)) { throw "budget.$key ausente." }
    }
    # ConvertFrom-Json pode transformar ISO 8601 em DateTime nas versoes recentes do PowerShell.
    $end = try { [DateTimeOffset]$Config.budget.sessionEndsAtUtc } catch { [DateTimeOffset]::MinValue }
    if ([string]::IsNullOrWhiteSpace($Config.budget.approvedBy) -or [string]::IsNullOrWhiteSpace($Config.budget.reference) -or
        $Config.budget.maxUsd -le 0 -or $Config.budget.estimatedSessionUsd -le 0 -or
        $Config.budget.estimatedSessionUsd -gt $Config.budget.maxUsd -or
        $end -le [DateTimeOffset]::UtcNow) {
        throw 'Registre aprovacao real do grupo, referencia, limite, estimativa positiva dentro do limite e fim futuro da sessao em budget. Isto nao e um teto automatico de cobranca.'
    }
    if ($Config.feasibility.fargateConfirmed -ne $true -or $Config.feasibility.passRoleConfirmed -ne $true) {
        throw 'Confirme as restricoes de Fargate e iam:PassRole no checklist antes de provisionar.'
    }
}

function Invoke-Tool {
    param([string]$File, [string[]]$Arguments, [string]$InputText)
    $start = [Diagnostics.ProcessStartInfo]::new()
    $start.FileName = $File
    $start.UseShellExecute = $false
    $start.CreateNoWindow = $true
    $start.RedirectStandardOutput = $true
    $start.RedirectStandardError = $true
    $start.RedirectStandardInput = $true
    $start.Environment['AWS_EC2_METADATA_DISABLED'] = 'true'
    foreach ($argument in $Arguments) { $start.ArgumentList.Add($argument) }
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $start
    try {
        $null = $process.Start()
        $stdout = $process.StandardOutput.ReadToEndAsync()
        $stderr = $process.StandardError.ReadToEndAsync()
        if ($PSBoundParameters.ContainsKey('InputText')) { $process.StandardInput.WriteLine($InputText) }
        $process.StandardInput.Close()
        $process.WaitForExit()
        $output = $stdout.GetAwaiter().GetResult()
        $errorOutput = $stderr.GetAwaiter().GetResult()
        if ($process.ExitCode -ne 0) { throw "Falha em $([IO.Path]::GetFileName($File)): $errorOutput" }
        return $output
    } finally { $process.Dispose() }
}

function Get-AwsExecutable {
    foreach ($installed in @((Join-Path $env:LOCALAPPDATA 'Programs/Amazon/AWSCLIV2/aws.exe'), (Join-Path $env:USERPROFILE 'AppData/Local/Programs/Amazon/AWSCLIV2/aws.exe'), (Join-Path $env:ProgramFiles 'Amazon/AWSCLIV2/aws.exe'))) {
        if (Test-Path -LiteralPath $installed) { return $installed }
    }
    $command = Get-Command aws -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw 'AWS CLI v2 ausente. Execute Setup-AwsCli.ps1 e abra novamente o terminal.'
}

function Invoke-Aws {
    param($Config, [string[]]$Arguments, [switch]$Raw, [string[]]$NotFoundCodes = @())
    $argsList = @($Arguments) + @('--profile', $Config.profile, '--region', $Config.region, '--output', 'json', '--no-cli-pager', '--no-cli-auto-prompt', '--cli-connect-timeout', '10', '--cli-read-timeout', '30')
    try { $output = Invoke-Tool -File (Get-AwsExecutable) -Arguments $argsList }
    catch {
        foreach ($code in $NotFoundCodes) { if ($_.Exception.Message -match "\($([regex]::Escape($code))\)") { return $null } }
        throw
    }
    if ($Raw) { return $output.Trim() }
    if ([string]::IsNullOrWhiteSpace($output)) { return @{} }
    return ($output | ConvertFrom-Json -AsHashtable)
}

function Assert-Identity {
    param($Config, [switch]$Discovery)
    Assert-AccountConfig $Config -Discovery:$Discovery
    $identity = Invoke-Aws $Config @('sts', 'get-caller-identity')
    if ($Config.accountId -and $identity.Account -ne $Config.accountId) { throw "Conta diferente da configurada. Recebida: $($identity.Account). Nenhuma alteracao autorizada." }
    return $identity
}

function Get-StatePath { param($Config) return (Join-Path $script:InfraRoot ".state/$($Config.accountId)-$($Config.region)-$($Config.project).json") }
function Save-State { param($Config, $State) Write-Json (Get-StatePath $Config) $State }
function Assert-InfrastructureShape {
    param($Config, $State)
    $shape = [ordered]@{vpcId = $Config.vpcId; subnetIds = @($Config.subnetIds | Sort-Object); useAlb = $Config.useAlb; port = $Config.containerPort; allowedCidrs = @($Config.allowedCidrs | Sort-Object)} | ConvertTo-Json -Compress
    if ($State.ContainsKey('networkShape') -and $State.networkShape -ne $shape) {
        $activeKeys = @('cluster', 'service', 'taskSecurityGroup', 'albSecurityGroup', 'loadBalancer', 'targetGroup', 'listener')
        if (@($activeKeys | Where-Object { $State.resources.ContainsKey($_) }).Count) { throw 'Rede, porta ou modo ALB mudaram desde o provisionamento. Remova a infraestrutura anterior antes de alterar esses campos.' }
    }
    if (-not $State.ContainsKey('networkShape') -or $State.networkShape -ne $shape) { $State.networkShape = $shape; Save-State $Config $State }
}

function Assert-DescribeFailures {
    param($Response)
    if (@($Response.failures | Where-Object { $_.reason -ne 'MISSING' }).Count) { throw 'A AWS retornou uma falha de consulta diferente de MISSING. Inventario preservado.' }
}
function Read-State {
    param($Config, [switch]$Create)
    $path = Get-StatePath $Config
    if (Test-Path -LiteralPath $path) {
        $state = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json -AsHashtable
        if ($state.accountId -ne $Config.accountId -or $state.region -ne $Config.region -or $state.project -ne $Config.project) { throw 'Inventario nao corresponde a conta, regiao e projeto.' }
        return $state
    }
    if (-not $Create) { throw 'Inventario ausente. Execute Provision.ps1; nao importe recursos de terceiros automaticamente.' }
    $state = @{schemaVersion = 1; accountId = $Config.accountId; region = $Config.region; project = $Config.project; deploymentId = [guid]::NewGuid().ToString(); resources = @{}; taskDefinitions = @()}
    Save-State $Config $state
    return $state
}

function Get-ResourceTags {
    param($Config, $State)
    return @(@{key = 'Project'; value = $Config.project}, @{key = 'ManagedBy'; value = 'richard-strauss-scripts'}, @{key = 'DeploymentId'; value = $State.deploymentId})
}

function Assert-Owned {
    param($Config, $State, $Resource)
    switch ($Resource.kind) {
        'ec2' { $r = Invoke-Aws $Config @('ec2', 'describe-security-groups', '--group-ids', $Resource.id); $tags = $r.SecurityGroups[0].Tags }
        'ecr' { $tags = (Invoke-Aws $Config @('ecr', 'list-tags-for-resource', '--resource-arn', $Resource.arn)).tags }
        'ecs' { $tags = (Invoke-Aws $Config @('ecs', 'list-tags-for-resource', '--resource-arn', $Resource.arn)).tags }
        'logs' { $tagMap = (Invoke-Aws $Config @('logs', 'list-tags-for-resource', '--resource-arn', $Resource.arn)).tags; $tags = @($tagMap.Keys | ForEach-Object { @{key = $_; value = $tagMap[$_]} }) }
        'elbv2' { $tags = (Invoke-Aws $Config @('elbv2', 'describe-tags', '--resource-arns', $Resource.arn)).TagDescriptions[0].Tags }
        'aas' { $tagMap = (Invoke-Aws $Config @('application-autoscaling', 'list-tags-for-resource', '--resource-arn', $Resource.arn)).Tags; $tags = @($tagMap.Keys | ForEach-Object { @{key = $_; value = $tagMap[$_]} }) }
        default { throw "Tipo de recurso desconhecido: $($Resource.kind)" }
    }
    $actual = @{}
    foreach ($tag in $tags) {
        $key = $tag['key'] ?? $tag['Key']
        $value = $tag['value'] ?? $tag['Value']
        if ($key) { $actual[$key] = $value }
    }
    foreach ($tag in (Get-ResourceTags $Config $State)) {
        if (-not $actual.ContainsKey($tag.key) -or $actual[$tag.key] -ne $tag.value) { throw "Propriedade nao comprovada para $($Resource.id): tag $($tag.key). Recurso preservado." }
    }
}

function Get-ScalableResourceId { param($Config) return "service/$($Config.project)/$($Config.project)-api" }

function Assert-AutoScalingParameters {
    param([int]$MinTasks, [int]$MaxTasks, [double]$TargetCpu, [int]$ScaleOutCooldown, [int]$ScaleInCooldown)
    # Limite do plano da equipe: no maximo tres tasks durante os testes.
    if ($MinTasks -lt 1 -or $MaxTasks -gt 3 -or $MinTasks -gt $MaxTasks) { throw 'Auto Scaling: use 1 <= MinTasks <= MaxTasks <= 3 (limite do plano).' }
    if ($TargetCpu -lt 10 -or $TargetCpu -gt 90) { throw 'Auto Scaling: TargetCpu deve ficar entre 10 e 90.' }
    foreach ($cooldown in @($ScaleOutCooldown, $ScaleInCooldown)) { if ($cooldown -lt 0 -or $cooldown -gt 3600) { throw 'Auto Scaling: cooldowns entre 0 e 3600 s.' } }
}

function New-ScalableTargetRequest {
    param($Config, $State, [int]$MinTasks, [int]$MaxTasks, [switch]$WithTags)
    $request = [ordered]@{ServiceNamespace = 'ecs'; ResourceId = (Get-ScalableResourceId $Config); ScalableDimension = 'ecs:service:DesiredCount'; MinCapacity = $MinTasks; MaxCapacity = $MaxTasks}
    # Tags so na criacao: comprovam a propriedade antes de alterar ou remover o scalable target.
    if ($WithTags) { $tags = [ordered]@{}; foreach ($tag in (Get-ResourceTags $Config $State)) { $tags[$tag.key] = $tag.value }; $request.Tags = $tags }
    return $request
}

function New-ScalingPolicyRequest {
    param($Config, [double]$TargetCpu, [int]$ScaleOutCooldown, [int]$ScaleInCooldown)
    return [ordered]@{
        PolicyName = "$($Config.project)-cpu"; ServiceNamespace = 'ecs'; ResourceId = (Get-ScalableResourceId $Config); ScalableDimension = 'ecs:service:DesiredCount'
        PolicyType = 'TargetTrackingScaling'
        TargetTrackingScalingPolicyConfiguration = [ordered]@{
            TargetValue = $TargetCpu
            PredefinedMetricSpecification = @{PredefinedMetricType = 'ECSServiceAverageCPUUtilization'}
            ScaleOutCooldown = $ScaleOutCooldown; ScaleInCooldown = $ScaleInCooldown; DisableScaleIn = $false
        }
    }
}

function Add-Resource {
    param($Config, $State, [string]$Key, [string]$Kind, [string]$Id, [string]$Arn)
    $State.resources[$Key] = @{kind = $Kind; id = $Id; arn = $Arn}
    Save-State $Config $State
}

function Write-Request {
    param([string]$Name, $Value)
    $path = Join-Path $script:InfraRoot "generated/$Name.json"
    Write-Json $path $Value
    return "file://$([IO.Path]::GetFullPath($path))"
}

function Assert-PublicNetwork {
    param($Config)
    $response = Invoke-Aws $Config (@('ec2', 'describe-subnets', '--subnet-ids') + @($Config.subnetIds))
    $zones = @()
    foreach ($subnet in $response.Subnets) {
        if ($subnet.VpcId -ne $Config.vpcId -or $subnet.State -ne 'available') { throw "Subnet $($subnet.SubnetId) nao pertence a VPC ou esta indisponivel." }
        if ($Config.useAlb -and $subnet.AvailableIpAddressCount -lt 8) { throw 'ALB exige pelo menos 8 enderecos livres por subnet.' }
        $zones += $subnet.AvailabilityZone
        $tables = (Invoke-Aws $Config @('ec2', 'describe-route-tables', '--filters', "Name=association.subnet-id,Values=$($subnet.SubnetId)")).RouteTables
        if (@($tables).Count -eq 0) { $tables = (Invoke-Aws $Config @('ec2', 'describe-route-tables', '--filters', "Name=vpc-id,Values=$($Config.vpcId)", 'Name=association.main,Values=true')).RouteTables }
        $publicRoutes = @($tables | ForEach-Object { $_.Routes } | Where-Object { $_.ContainsKey('DestinationCidrBlock') -and $_.DestinationCidrBlock -eq '0.0.0.0/0' -and $_.ContainsKey('GatewayId') -and $_.GatewayId -like 'igw-*' -and $_.State -eq 'active' })
        if ($publicRoutes.Count -eq 0) { throw "Subnet $($subnet.SubnetId) nao tem rota publica ativa para Internet Gateway." }
    }
    if ($Config.useAlb -and @($zones | Select-Object -Unique).Count -lt 2) { throw 'ALB exige subnets em duas zonas de disponibilidade distintas.' }
}

function New-DeploymentSpec {
    param($Config, [string]$ImageUri, [string]$SecurityGroupId, [string]$TargetGroupArn = '', [string]$DeploymentId = 'offline-preview')
    Assert-DeploymentConfig $Config
    $expected = "$($Config.accountId).dkr.ecr.$($Config.region).amazonaws.com/$($Config.project)@sha256:"
    if (-not $ImageUri.StartsWith($expected) -or $ImageUri.Substring($expected.Length) -cnotmatch '^[a-f0-9]{64}$') { throw 'Use a URI ECR do projeto fixada por digest sha256.' }
    if ($SecurityGroupId -notmatch '^sg-[a-f0-9]+$') { throw 'SecurityGroupId invalido.' }
    if ($Config.useAlb -and -not $TargetGroupArn.StartsWith("arn:aws:elasticloadbalancing:$($Config.region):$($Config.accountId):targetgroup/")) { throw 'Informe TargetGroupArn da conta e regiao para ALB.' }
    $task = Get-Content -LiteralPath (Join-Path $script:InfraRoot 'templates/task-definition.json') -Raw | ConvertFrom-Json -AsHashtable
    $task.family = "$($Config.project)-api"
    $task.executionRoleArn = $Config.executionRoleArn
    $container = $task.containerDefinitions[0]
    $container.image = $ImageUri
    $container.portMappings[0].containerPort = $Config.containerPort
    # A API escuta em PORT: derivar de containerPort mantem mapeamento, health check e ALB na mesma porta.
    $container.environment = @(@($Config.environment | Where-Object { $_.name -ne 'PORT' }) + @(@{name = 'PORT'; value = [string]$Config.containerPort}))
    # Health check leve (socket da biblioteca padrao, sem urllib/ssl): em 0,25 vCPU custa ~1/3 da CPU da versao com urllib.
    $container.healthCheck.command[-1] = "import socket,sys; s=socket.create_connection(('127.0.0.1',$($Config.containerPort)),4); s.sendall(b'GET /health HTTP/1.0\r\n\r\n'); sys.exit(0 if s.makefile('rb').readline().split()[1:2]==[b'200'] else 1)"
    $container.logConfiguration.options['awslogs-group'] = "/ecs/$($Config.project)"
    $container.logConfiguration.options['awslogs-region'] = $Config.region
    $tags = Get-ResourceTags $Config @{deploymentId = $DeploymentId}
    $task.tags = $tags
    $service = Get-Content -LiteralPath (Join-Path $script:InfraRoot 'templates/service.json') -Raw | ConvertFrom-Json -AsHashtable
    $service.cluster = $Config.project
    $service.serviceName = "$($Config.project)-api"
    $service.taskDefinition = $task.family
    $service.desiredCount = $Config.desiredCount
    $service.networkConfiguration.awsvpcConfiguration.subnets = @($Config.subnetIds)
    $service.networkConfiguration.awsvpcConfiguration.securityGroups = @($SecurityGroupId)
    $service.tags = $tags
    if ($Config.useAlb) {
        $service.loadBalancers = @(@{targetGroupArn = $TargetGroupArn; containerName = 'api'; containerPort = $Config.containerPort})
        $service.healthCheckGracePeriodSeconds = 60
    }
    return @{task = $task; service = $service}
}

function Get-DeploymentSnapshot {
    param($Config, $State)
    $snapshot = [ordered]@{timestampUtc = [DateTimeOffset]::UtcNow.ToString('o'); accountId = $Config.accountId; region = $Config.region; project = $Config.project; service = $null; tasks = @(); endpoints = @(); targetHealth = @(); logStreams = @(); metrics = @{}}
    if ($State.resources.ContainsKey('service')) {
        $response = Invoke-Aws $Config @('ecs', 'describe-services', '--cluster', $Config.project, '--services', $State.resources.service.id)
        if (@($response.failures).Count -gt 0 -or @($response.services).Count -ne 1) { throw 'Servico do inventario nao encontrado no ECS.' }
        $snapshot.service = $response.services[0]
        $taskArns = (Invoke-Aws $Config @('ecs', 'list-tasks', '--cluster', $Config.project, '--service-name', $State.resources.service.id)).taskArns
        if (@($taskArns).Count -gt 0) {
            $description = Invoke-Aws $Config (@('ecs', 'describe-tasks', '--cluster', $Config.project, '--tasks') + @($taskArns))
            if (@($description.failures).Count) { throw 'Nao foi possivel descrever todas as tasks.' }
            $snapshot.tasks = @($description.tasks)
            if (-not $Config.useAlb) {
                foreach ($task in $description.tasks) {
                    $eni = @($task.attachments | ForEach-Object { $_.details } | Where-Object { $_.name -eq 'networkInterfaceId' })
                    if ($eni.Count) {
                        $network = (Invoke-Aws $Config @('ec2', 'describe-network-interfaces', '--network-interface-ids', $eni[0].value)).NetworkInterfaces[0]
                        if ($network.ContainsKey('Association') -and $network.Association.ContainsKey('PublicIp')) {
                            $snapshot.endpoints += "http://$($network.Association.PublicIp):$($Config.containerPort)"
                        }
                    }
                }
            }
        }
        $end = [DateTimeOffset]::UtcNow
        foreach ($metric in @('CPUUtilization', 'MemoryUtilization')) {
            $snapshot.metrics[$metric] = Invoke-Aws $Config @('cloudwatch', 'get-metric-statistics', '--namespace', 'AWS/ECS', '--metric-name', $metric, '--dimensions', "Name=ClusterName,Value=$($Config.project)", "Name=ServiceName,Value=$($State.resources.service.id)", '--start-time', $end.AddMinutes(-15).ToString('o'), '--end-time', $end.ToString('o'), '--period', '60', '--statistics', 'Average')
        }
    }
    if ($State.resources.ContainsKey('loadBalancer')) {
        $lb = (Invoke-Aws $Config @('elbv2', 'describe-load-balancers', '--load-balancer-arns', $State.resources.loadBalancer.arn)).LoadBalancers[0]
        $snapshot.endpoints = @("http://$($lb.DNSName)")
    }
    if ($State.resources.ContainsKey('targetGroup')) { $snapshot.targetHealth = (Invoke-Aws $Config @('elbv2', 'describe-target-health', '--target-group-arn', $State.resources.targetGroup.arn)).TargetHealthDescriptions }
    if ($State.resources.ContainsKey('logGroup')) { $snapshot.logStreams = (Invoke-Aws $Config @('logs', 'describe-log-streams', '--log-group-name', $State.resources.logGroup.id, '--order-by', 'LastEventTime', '--descending', '--limit', '10')).logStreams }
    if ($State.ContainsKey('image')) { $snapshot.image = $State.image }
    return $snapshot
}
