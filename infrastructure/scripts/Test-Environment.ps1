#Requires -Version 7.2
[CmdletBinding()]
param([string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'), [switch]$Offline)
. "$PSScriptRoot/Common.ps1"
$report = [ordered]@{timestampUtc = [DateTimeOffset]::UtcNow.ToString('o'); mode = $(if ($Offline) {'offline'} else {'read-only'}); checks = @(); pending = @('Creditos, limite e janela de gastos do grupo', 'Restricoes do laboratorio e duracao das credenciais', 'Fargate e iam:PassRole: consultas de leitura nao comprovam permissao de criacao')}
foreach ($name in @('aws', 'docker', 'git')) {
    $available = $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
    if ($name -eq 'aws') { try { $null = Get-AwsExecutable; $available = $true } catch { $available = $false } }
    $report.checks += @{item = $name; status = $(if ($available) {'disponivel'} else {'ausente'})}
}
if (Get-Command docker -ErrorAction SilentlyContinue) {
    try { $version = Invoke-Tool (Get-Command docker).Source @('version', '--format', '{{.Server.Version}}'); $report.checks += @{item = 'Docker engine'; status = 'disponivel'; version = $version.Trim()} }
    catch { $report.checks += @{item = 'Docker engine'; status = 'indisponivel'; detail = 'Inicie Docker Desktop antes de construir a imagem.'} }
}
if (-not $Offline) {
    $config = Read-Config $ConfigPath
    $identity = Assert-Identity $config -Discovery
    $report.accountId = $identity.Account
    $report.region = $config.region
    $report.principalArn = $identity.Arn
    $probes = @(
        @{name = 'ECS'; args = @('ecs', 'list-clusters', '--max-results', '1')},
        @{name = 'ECR'; args = @('ecr', 'describe-repositories', '--max-results', '1')},
        @{name = 'CloudWatch Logs'; args = @('logs', 'describe-log-groups', '--limit', '1')},
        @{name = 'CloudWatch Metrics'; args = @('cloudwatch', 'list-metrics', '--namespace', 'AWS/ECS', '--no-paginate')},
        @{name = 'Rede'; args = @('ec2', 'describe-vpcs')},
        @{name = 'ALB'; args = @('elbv2', 'describe-load-balancers', '--page-size', '1', '--no-paginate')}
    )
    if ($config.executionRoleArn) { $probes += @{name = 'Execution role IAM'; args = @('iam', 'get-role', '--role-name', ($config.executionRoleArn -split '/')[-1])} }
    foreach ($probe in $probes) {
        try { $null = Invoke-Aws $config $probe.args; $report.checks += @{item = $probe.name; status = 'consulta permitida'} }
        catch { $report.checks += @{item = $probe.name; status = 'bloqueado ou indisponivel'; detail = $_.Exception.Message} }
    }
    if ($config.vpcId -and @($config.subnetIds).Count -gt 0) {
        try { Assert-PublicNetwork $config; $report.checks += @{item = 'Subnets e rotas'; status = 'validas'} }
        catch { $report.checks += @{item = 'Subnets e rotas'; status = 'bloqueado'; detail = $_.Exception.Message} }
    }
}
$path = Join-Path $script:InfraRoot ('evidence/environment-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '.json')
Write-Json $path $report
$report.checks | ForEach-Object { Write-Host "$($_.item): $($_.status)" }
Write-Host "Relatorio: $path. A viabilidade permanece pendente ate confirmar os itens do checklist."
