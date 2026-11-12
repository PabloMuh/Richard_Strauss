#Requires -Version 7.2
[CmdletBinding()]
param([switch]$ValidateCliShapes)
. "$PSScriptRoot/../scripts/Common.ps1"
$script:Passed = 0
$script:Failed = 0
function Test-Case {
    param([string]$Name, [scriptblock]$Body)
    try { & $Body; $script:Passed++; Write-Host "OK  $Name" }
    catch { $script:Failed++; Write-Host "FAIL $Name : $($_.Exception.Message)" -ForegroundColor Red }
}
function Assert-True { param([bool]$Value, [string]$Message = 'Condicao nao satisfeita') if (-not $Value) { throw $Message } }
function Assert-Throws {
    param([scriptblock]$Body, [string]$Pattern)
    $caught = $null
    try { & $Body | Out-Null } catch { $caught = $_.Exception.Message }
    if (-not $caught -or ($Pattern -and $caught -notmatch $Pattern)) { throw "Excecao esperada ($Pattern); recebida: $caught" }
}
function Copy-Fixture { return ($script:Fixture | ConvertTo-Json -Depth 100 | ConvertFrom-Json -AsHashtable) }
$script:Fixture = Get-Content -LiteralPath (Join-Path $script:InfraRoot 'config.example.json') -Raw | ConvertFrom-Json -AsHashtable
$script:Fixture.profile = 'offline-tests'
$script:Fixture.region = 'us-east-1'
$script:Fixture.accountId = '123456789012'
$script:Fixture.vpcId = 'vpc-0123456789abcdef0'
$script:Fixture.subnetIds = @('subnet-0123456789abcdef0', 'subnet-abcdef01234567890')
$script:Fixture.executionRoleArn = 'arn:aws:iam::123456789012:role/ecsTaskExecutionRole'
$script:Fixture.allowedCidrs = @('203.0.113.10/32')
$script:Fixture.imageTag = 'api-test'
$script:Fixture.feasibility.fargateConfirmed = $true
$script:Fixture.feasibility.passRoleConfirmed = $true
$script:Fixture.budget = @{approvedBy = 'offline-fixture'; reference = 'test-only'; maxUsd = 1; estimatedSessionUsd = 0.5; sessionEndsAtUtc = [DateTimeOffset]::UtcNow.AddHours(1).ToString('o')}
$image = '123456789012.dkr.ecr.us-east-1.amazonaws.com/richard-strauss@sha256:' + ('a' * 64)
$originalAws = ${function:Invoke-Aws}
$script:AwsCalls = @()
$script:FakeHandler = { param($Arguments) throw "Chamada AWS nao prevista no teste: $Arguments" }
function Invoke-Aws {
    param($Config, [string[]]$Arguments, [switch]$Raw, [string[]]$NotFoundCodes = @())
    $script:AwsCalls += ,$Arguments
    return (& $script:FakeHandler $Arguments)
}
$testRoot = Join-Path $script:InfraRoot ('generated/tests-' + [guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($testRoot) | Out-Null
try {
    Test-Case 'Todos os scripts PowerShell possuem sintaxe valida' {
        foreach ($file in (Get-ChildItem -LiteralPath (Join-Path $script:InfraRoot 'scripts') -Filter '*.ps1')) {
            $tokens = $null; $errors = $null
            $null = [Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors)
            Assert-True (@($errors).Count -eq 0) "$($file.Name): $errors"
        }
    }
    Test-Case 'JSONs versionados podem ser lidos' {
        foreach ($file in (Get-ChildItem -LiteralPath $script:InfraRoot -Recurse -Filter '*.json' | Where-Object { $_.FullName -notmatch '[\\/](generated|evidence|\.state)[\\/]' })) {
            $null = Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json -AsHashtable
        }
    }
    Test-Case 'Configuracao de exemplo nao autoriza operacoes AWS' {
        $config = Read-Config (Join-Path $script:InfraRoot 'config.example.json')
        Assert-Throws { Assert-AccountConfig $config } 'profile'
        Assert-Throws { Assert-SpendingWindow $config } 'aprovacao'
        Assert-True ($script:AwsCalls.Count -eq 0)
    }
    Test-Case 'Configuracao local ausente apresenta instrucao util' {
        Assert-Throws { Read-Config (Join-Path $testRoot 'missing.json') } 'Copie'
    }
    Test-Case 'Configuracao completa e estruturalmente valida' {
        Write-Json (Join-Path $testRoot 'config.json') $script:Fixture
        $config = Read-Config (Join-Path $testRoot 'config.json')
        Assert-DeploymentConfig $config
        Assert-SpendingWindow $config
    }
    Test-Case 'Regiao e account ID sao obrigatorios antes de mutacoes' {
        $config = Copy-Fixture; $config.region = ''
        Assert-Throws { Assert-AccountConfig $config } 'regiao'
        $config = Copy-Fixture; $config.accountId = ''
        Assert-Throws { Assert-AccountConfig $config } '12 digitos'
    }
    Test-Case 'Conta errada e bloqueada apos STS e antes de mutacoes' {
        $script:FakeHandler = { param($Arguments) return @{Account = '999999999999'; Arn = 'test'} }
        $before = $script:AwsCalls.Count
        Assert-Throws { Assert-Identity (Copy-Fixture) } 'Conta diferente'
        Assert-True ($script:AwsCalls.Count -eq ($before + 1))
        Assert-True ($script:AwsCalls[-1][0] -eq 'sts')
    }
    Test-Case 'Janela expirada impede gasto' {
        $config = Copy-Fixture; $config.budget.sessionEndsAtUtc = [DateTimeOffset]::UtcNow.AddMinutes(-1).ToString('o')
        Assert-Throws { Assert-SpendingWindow $config } 'fim futuro'
    }
    Test-Case 'Estimativa acima do limite impede gasto' {
        $config = Copy-Fixture; $config.budget.estimatedSessionUsd = 2
        Assert-Throws { Assert-SpendingWindow $config } 'limite'
    }
    Test-Case 'PassRole ainda nao confirmado impede provisionamento' {
        $config = Copy-Fixture; $config.feasibility.passRoleConfirmed = $false
        Assert-Throws { Assert-SpendingWindow $config } 'PassRole'
    }
    Test-Case 'CIDR aberto, rede /24 e IPv6 sao rejeitados' {
        foreach ($cidr in @('0.0.0.0/0', '203.0.113.0/24', '::1/32', '999.1.2.3/32')) {
            $config = Copy-Fixture; $config.allowedCidrs = @($cidr)
            Assert-Throws { Assert-DeploymentConfig $config } 'IPv4 /32'
        }
    }
    Test-Case 'Role de outra conta e rejeitada' {
        $config = Copy-Fixture; $config.executionRoleArn = 'arn:aws:iam::999999999999:role/other'
        Assert-Throws { Assert-DeploymentConfig $config } 'conta do trabalho'
    }
    Test-Case 'Preview direto usa digest, porta, PORT e health check leve sem curl' {
        $config = Copy-Fixture; $config.containerPort = 8081
        $spec = New-DeploymentSpec $config $image 'sg-0123456789abcdef0'
        Assert-True ($spec.task.containerDefinitions[0].image -eq $image)
        Assert-True ($spec.task.containerDefinitions[0].portMappings[0].containerPort -eq 8081)
        $health = $spec.task.containerDefinitions[0].healthCheck
        Assert-True ($health.command[1] -eq 'python')
        Assert-True ($health.command[-1] -match "\('127\.0\.0\.1',8081\)" -and $health.command[-1] -match 'GET /health ') 'Health check deve consultar /health na porta configurada'
        Assert-True ($health.command[-1] -notmatch 'urllib') 'Health check deve evitar urllib (custo de CPU em 0,25 vCPU)'
        Assert-True ($health.timeout -eq 10)
        Assert-True (@($spec.task.containerDefinitions[0].environment | Where-Object { $_.name -eq 'PORT' -and $_.value -eq '8081' }).Count -eq 1) 'PORT deve acompanhar containerPort'
        Assert-True (-not $spec.task.ContainsKey('taskRoleArn'))
        Assert-True (-not $spec.service.ContainsKey('loadBalancers'))
        Assert-True ($spec.service.networkConfiguration.awsvpcConfiguration.assignPublicIp -eq 'ENABLED')
        Assert-True ($spec.task.cpu -eq '256' -and $spec.task.memory -eq '512')
    }
    Test-Case 'Preview ALB configura target e grace period' {
        $config = Copy-Fixture; $config.useAlb = $true; $config.desiredCount = 2
        $arn = 'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/test/abc'
        $spec = New-DeploymentSpec $config $image 'sg-0123456789abcdef0' $arn
        Assert-True ($spec.service.loadBalancers[0].targetGroupArn -eq $arn)
        Assert-True ($spec.service.desiredCount -eq 2 -and $spec.service.healthCheckGracePeriodSeconds -eq 60)
    }
    Test-Case 'ALB exige target group e duas subnets diferentes' {
        $config = Copy-Fixture; $config.useAlb = $true
        Assert-Throws { New-DeploymentSpec $config $image 'sg-0123456789abcdef0' } 'TargetGroupArn'
        $config.subnetIds = @($config.subnetIds[0], $config.subnetIds[0])
        Assert-Throws { Assert-DeploymentConfig $config } 'duas zonas'
    }
    Test-Case 'Imagem mutavel, digest invalido ou registry externo sao rejeitados' {
        foreach ($uri in @('nginx:latest', $image.Replace('sha256:', 'tag:'), $image.Replace('123456789012', '999999999999'), $image.Substring(0, $image.Length - 1))) {
            Assert-Throws { New-DeploymentSpec (Copy-Fixture) $uri 'sg-0123456789abcdef0' } 'digest'
        }
    }
    Test-Case 'Sem rota para IGW o provisionamento e bloqueado' {
        $script:FakeHandler = {
            param($Arguments)
            if ($Arguments[1] -eq 'describe-subnets') { return @{Subnets = @(@{VpcId = 'vpc-0123456789abcdef0'; SubnetId = 'subnet-0123456789abcdef0'; State = 'available'; AvailabilityZone = 'us-east-1a'; AvailableIpAddressCount = 20})} }
            return @{RouteTables = @(@{Routes = @(@{DestinationCidrBlock = '0.0.0.0/0'; NatGatewayId = 'nat-test'; State = 'active'})})}
        }
        Assert-Throws { Assert-PublicNetwork (Copy-Fixture) } 'Internet Gateway'
    }
    Test-Case 'Rota principal da VPC e usada quando nao ha associacao explicita' {
        $script:FakeHandler = {
            param($Arguments)
            if ($Arguments[1] -eq 'describe-subnets') { return @{Subnets = @(@{VpcId = 'vpc-0123456789abcdef0'; SubnetId = 'subnet-0123456789abcdef0'; State = 'available'; AvailabilityZone = 'us-east-1a'; AvailableIpAddressCount = 20})} }
            if ($Arguments -contains 'Name=association.main,Values=true') { return @{RouteTables = @(@{Routes = @(@{DestinationCidrBlock = '0.0.0.0/0'; GatewayId = 'igw-test'; State = 'active'})})} }
            return @{RouteTables = @()}
        }
        Assert-PublicNetwork (Copy-Fixture)
    }
    Test-Case 'Duas subnets na mesma AZ nao satisfazem ALB' {
        $script:FakeHandler = {
            param($Arguments)
            if ($Arguments[1] -eq 'describe-subnets') { return @{Subnets = @('subnet-0123456789abcdef0', 'subnet-abcdef01234567890' | ForEach-Object { @{VpcId = 'vpc-0123456789abcdef0'; SubnetId = $_; State = 'available'; AvailabilityZone = 'us-east-1a'; AvailableIpAddressCount = 20} })} }
            return @{RouteTables = @(@{Routes = @(@{DestinationCidrBlock = '0.0.0.0/0'; GatewayId = 'igw-test'; State = 'active'})})}
        }
        $config = Copy-Fixture; $config.useAlb = $true
        Assert-Throws { Assert-PublicNetwork $config } 'distintas'
    }
    Test-Case 'Tags corretas comprovam propriedade' {
        $script:FakeHandler = { param($Arguments) return @{tags = @(@{key = 'Project'; value = 'richard-strauss'}, @{key = 'ManagedBy'; value = 'richard-strauss-scripts'}, @{key = 'DeploymentId'; value = 'test-deploy'})} }
        Assert-Owned (Copy-Fixture) @{deploymentId = 'test-deploy'} @{kind = 'ecs'; id = 'test'; arn = 'test'}
    }
    Test-Case 'Recurso de outro deployment e preservado' {
        Assert-Throws { Assert-Owned (Copy-Fixture) @{deploymentId = 'different'} @{kind = 'ecs'; id = 'test'; arn = 'test'} } 'Propriedade nao comprovada'
    }
    Test-Case 'Tags no formato real de cada servico comprovam propriedade (ECS, Logs, ECR, EC2, ELB)' {
        # As respostas passam por ConvertFrom-Json -AsHashtable, como no Invoke-Aws real: o resultado
        # diferencia maiusculas de minusculas, ao contrario de hashtables literais @{}. ECR, EC2 e ELB
        # usam Key/Value; ECS usa key/value; Logs devolve um mapa.
        $upper = '[{"Key":"Project","Value":"richard-strauss"},{"Key":"ManagedBy","Value":"richard-strauss-scripts"},{"Key":"DeploymentId","Value":"test-deploy"}]'
        $lower = $upper.Replace('"Key"', '"key"').Replace('"Value"', '"value"')
        $script:Responses = @{
            ecs   = "{`"tags`":$lower}"
            logs  = '{"tags":{"Project":"richard-strauss","ManagedBy":"richard-strauss-scripts","DeploymentId":"test-deploy"}}'
            ecr   = "{`"tags`":$upper}"
            ec2   = "{`"SecurityGroups`":[{`"GroupId`":`"sg-0123456789abcdef0`",`"Tags`":$upper}]}"
            elbv2 = "{`"TagDescriptions`":[{`"ResourceArn`":`"arn:test`",`"Tags`":$upper}]}"
        }
        $script:FakeHandler = { param($Arguments) return ($script:Responses[$Arguments[0]] | ConvertFrom-Json -AsHashtable) }
        foreach ($kind in @('ecs', 'logs', 'ecr', 'ec2', 'elbv2')) {
            try { Assert-Owned (Copy-Fixture) @{deploymentId = 'test-deploy'} @{kind = $kind; id = 'test'; arn = 'test'} }
            catch { throw "$kind nao reconhecido: $($_.Exception.Message)" }
            Assert-Throws { Assert-Owned (Copy-Fixture) @{deploymentId = 'different'} @{kind = $kind; id = 'test'; arn = 'test'} } 'Propriedade nao comprovada'
        }
    }
    Test-Case 'PORT em environment deve coincidir com containerPort e nao e duplicado' {
        $path = Join-Path $testRoot 'config-port.json'
        $config = Copy-Fixture; $config.environment = @(@{name = 'PORT'; value = '9000'})
        Write-Json $path $config
        Assert-Throws { Read-Config $path } 'PORT'
        $config.environment = @(@{name = 'PORT'; value = '8000'}, @{name = 'LOG_LEVEL'; value = 'DEBUG'})
        Write-Json $path $config
        $environment = @((New-DeploymentSpec (Read-Config $path) $image 'sg-0123456789abcdef0').task.containerDefinitions[0].environment)
        Assert-True (@($environment | Where-Object { $_.name -eq 'PORT' }).Count -eq 1) 'PORT duplicado'
        Assert-True (@($environment | Where-Object { $_.name -eq 'LOG_LEVEL' -and $_.value -eq 'DEBUG' }).Count -eq 1) 'Variaveis do usuario devem ser preservadas'
    }
    Test-Case 'Falha de permissao nao e tratada como recurso ausente' {
        $script:FakeHandler = { param($Arguments) throw 'An error occurred (AccessDeniedException)' }
        Assert-Throws { Assert-Owned (Copy-Fixture) @{deploymentId = 'test'} @{kind = 'ecs'; id = 'test'; arn = 'test'} } 'AccessDenied'
    }
    Test-Case 'Falhas ECS diferentes de MISSING nao sao ignoradas' {
        Assert-DescribeFailures @{failures = @(@{reason = 'MISSING'})}
        Assert-Throws { Assert-DescribeFailures @{failures = @(@{reason = 'ACCESS_DENIED'})} } 'diferente de MISSING'
    }
    Test-Case 'Preview executa como comando independente sem AWS' {
        $configPath = Join-Path $testRoot 'config.json'
        & (Join-Path $script:InfraRoot 'scripts/New-DeploymentFiles.ps1') -ConfigPath $configPath -ImageUri $image -SecurityGroupId 'sg-0123456789abcdef0' -OutputDirectory (Join-Path $testRoot 'preview')
        $task = Get-Content -LiteralPath (Join-Path $testRoot 'preview/task-definition.json') -Raw | ConvertFrom-Json -AsHashtable
        Assert-True ($task.containerDefinitions[0].image -eq $image)
    }
    Test-Case 'Estado grava IDs e rejeita rede modificada' {
        $realRoot = $script:InfraRoot
        try {
            $script:InfraRoot = $testRoot
            $config = Copy-Fixture
            $state = Read-State $config -Create
            Add-Resource $config $state 'cluster' 'ecs' 'richard-strauss' 'arn:test'
            Assert-InfrastructureShape $config $state
            $saved = Read-State $config
            Assert-True ($saved.resources.cluster.arn -eq 'arn:test')
            $config.useAlb = $true
            Assert-Throws { Assert-InfrastructureShape $config $saved } 'mudaram'
        } finally { $script:InfraRoot = $realRoot }
    }
    Test-Case 'Depois da limpeza e possivel mudar a rede e reprovisionar' {
        $realRoot = $script:InfraRoot
        try {
            $script:InfraRoot = $testRoot
            $config = Copy-Fixture
            $state = Read-State $config
            $state.resources.Clear()
            $config.useAlb = $true
            Assert-InfrastructureShape $config $state
            Assert-True ($state.networkShape -match '"useAlb":true')
        } finally { $script:InfraRoot = $realRoot }
    }
    Test-Case 'Inventario de outra conta ou regiao nao e aceito' {
        $realRoot = $script:InfraRoot
        try {
            $script:InfraRoot = $testRoot
            $config = Copy-Fixture
            $state = Read-State $config
            $state.accountId = '999999999999'; Save-State $config $state
            Assert-Throws { Read-State $config } 'Inventario nao corresponde'
        } finally { $script:InfraRoot = $realRoot }
    }
    Test-Case 'Processo nativo preserva argumentos com espacos e aspas' {
        $node = (Get-Command node -ErrorAction Stop).Source
        $payload = '{"name":"pasta com espacos","text":"aspas: \" e literal: $(x)"}'
        $output = Invoke-Tool $node @('-e', 'process.stdout.write(process.argv[1])', $payload)
        Assert-True ($output -ceq $payload)
    }
    if ($ValidateCliShapes) {
        # A CLI valida entrada contra o modelo real e envia somente para este stub de loopback.
        # Evita defeitos do --generate-cli-skeleton output em modelos com campos min > 0.
        $start = [Diagnostics.ProcessStartInfo]::new()
        $start.FileName = (Get-Command node -ErrorAction Stop).Source
        $start.UseShellExecute = $false
        $start.CreateNoWindow = $true
        $start.RedirectStandardOutput = $true
        $start.RedirectStandardError = $true
        $start.ArgumentList.Add('-e')
        $start.ArgumentList.Add('const http=require("http"); const s=http.createServer((q,r)=>{q.resume(); q.on("end",()=>{r.writeHead(200,{"content-type":"application/x-amz-json-1.1"});r.end("{}");});});s.listen(0,"127.0.0.1",()=>process.stdout.write(String(s.address().port)+"\n"));')
        $stub = [Diagnostics.Process]::new()
        $stub.StartInfo = $start
        $null = $stub.Start()
        $portTask = $stub.StandardOutput.ReadLineAsync()
        if (-not $portTask.Wait(5000)) { $stub.Kill($true); throw 'Stub HTTP local nao iniciou.' }
        $port = $portTask.GetAwaiter().GetResult()
        if ($port -notmatch '^\d+$') { $stub.Kill($true); throw 'Porta invalida no stub local.' }
        try {
        foreach ($alb in @($false, $true)) {
            Test-Case "AWS CLI valida JSON ECS contra stub local, sem AWS (ALB=$alb)" {
                $config = Copy-Fixture; $config.useAlb = $alb
                $target = if ($alb) { 'arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/test/1234567890123456' } else { '' }
                $spec = New-DeploymentSpec $config $image 'sg-0123456789abcdef0' $target
                $spec.service.taskDefinition = 'arn:aws:ecs:us-east-1:123456789012:task-definition/richard-strauss-api:1'
                foreach ($entry in @(@{operation = 'register-task-definition'; data = $spec.task}, @{operation = 'create-service'; data = $spec.service})) {
                    $jsonPath = Join-Path $testRoot ($entry.operation + '.json')
                    Write-Json $jsonPath $entry.data
                    $null = Invoke-Tool (Get-AwsExecutable) @('ecs', $entry.operation, '--cli-input-json', "file://$jsonPath", '--endpoint-url', "http://127.0.0.1:$port", '--region', 'us-east-1', '--no-sign-request', '--no-cli-pager', '--cli-connect-timeout', '2', '--cli-read-timeout', '2')
                }
            }
        }
        } finally { if (-not $stub.HasExited) { $stub.Kill($true); $stub.WaitForExit() }; $stub.Dispose() }
    }
} finally {
    Set-Item -Path Function:Invoke-Aws -Value $originalAws
    # Verifica o destino absoluto antes de qualquer remocao recursiva no Windows.
    $absolute = [IO.Path]::GetFullPath($testRoot)
    $allowedParent = [IO.Path]::GetFullPath((Join-Path $script:InfraRoot 'generated')) + [IO.Path]::DirectorySeparatorChar
    if (-not $absolute.StartsWith($allowedParent, [StringComparison]::OrdinalIgnoreCase) -or (Split-Path $absolute -Leaf) -notmatch '^tests-[a-f0-9]{32}$') { throw 'Destino temporario fora da pasta de testes.' }
    Remove-Item -LiteralPath $absolute -Recurse -Force
}
Write-Host "Resultado: $script:Passed aprovados; $script:Failed falhas. Nenhuma chamada real a AWS."
if ($script:Failed) { throw 'Os testes offline falharam.' }
