#Requires -Version 7.2
[CmdletBinding()]
param([string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'))
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
$null = Assert-Identity $config
$state = Read-State $config
$snapshot = Get-DeploymentSnapshot $config $state
$result = [ordered]@{timestampUtc = [DateTimeOffset]::UtcNow.ToString('o'); snapshot = $snapshot; http = @(); passed = $false; error = $null}
$path = Join-Path $script:InfraRoot ('evidence/smoke-' + [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '.json')
try {
    if (-not $snapshot.service -or $snapshot.service.desiredCount -ne $config.desiredCount -or $snapshot.service.runningCount -ne $config.desiredCount -or $snapshot.service.pendingCount -ne 0) { throw 'Quantidade de tasks ainda nao esta estavel.' }
    if (@($snapshot.tasks | Where-Object { $_.lastStatus -eq 'RUNNING' -and $_.ContainsKey('healthStatus') -and $_.healthStatus -eq 'HEALTHY' }).Count -ne $config.desiredCount) { throw 'Tasks ainda nao estao saudaveis.' }
    if (@($snapshot.endpoints).Count -eq 0) { throw 'Nenhum endpoint acessivel encontrado.' }
    if ($config.useAlb -and @($snapshot.targetHealth | Where-Object { $_.TargetHealth.State -eq 'healthy' }).Count -ne $config.desiredCount) { throw 'Targets do ALB ainda nao estao saudaveis.' }
    $ids = [Collections.Generic.HashSet[string]]::new()
    foreach ($endpoint in $snapshot.endpoints) {
        foreach ($route in @('health', 'instance', 'work')) {
            $response = Invoke-WebRequest -Uri "$endpoint/$route" -TimeoutSec 15 -MaximumRedirection 0
            if ($response.StatusCode -ne 200) { throw "HTTP invalido em /$route" }
            $body = $response.Content | ConvertFrom-Json -AsHashtable
            $result.http += @{endpoint = $endpoint; route = $route; status = $response.StatusCode; body = $body}
            if ($route -eq 'instance') {
                if (-not $body.ContainsKey('instance_id') -or [string]::IsNullOrWhiteSpace($body.instance_id)) { throw '/instance deve retornar instance_id textual e nao vazio, conforme o contrato de integracao.' }
                $null = $ids.Add([string]$body.instance_id)
            }
        }
    }
    if ($config.useAlb -and $config.desiredCount -eq 2) {
        for ($i = 0; $i -lt 40 -and $ids.Count -lt 2; $i++) {
            $response = Invoke-WebRequest -Uri "$($snapshot.endpoints[0])/instance" -TimeoutSec 10 -MaximumRedirection 0 -DisableKeepAlive
            $body = $response.Content | ConvertFrom-Json -AsHashtable
            if (-not $body.ContainsKey('instance_id')) { throw 'instance_id ausente.' }
            $null = $ids.Add([string]$body.instance_id)
            $result.http += @{endpoint = $snapshot.endpoints[0]; route = 'instance'; status = $response.StatusCode; body = $body}
        }
    }
    if ($ids.Count -ne $config.desiredCount) { throw 'Nao foi possivel distinguir todas as replicas. Preserve a evidencia e repita apos estabilizar.' }
    $snapshot = Get-DeploymentSnapshot $config $state
    $result.snapshot = $snapshot
    foreach ($task in $snapshot.tasks) {
        $taskId = ($task.taskArn -split '/')[-1]
        $streams = @($snapshot.logStreams | Where-Object { $_.logStreamName -eq "api/api/$taskId" -and $_.ContainsKey('lastEventTimestamp') })
        if ($streams.Count -eq 0) { throw "Sem evidencia de logs para task $taskId. A API deve gerar logs em stdout/stderr; aguarde a propagacao e repita." }
    }
    $result.passed = $true
    Write-Host 'Teste de fumaca aprovado: HTTP, replicas, saude e streams com eventos.'
} catch { $result.error = $_.Exception.Message; throw }
finally { Write-Json $path $result; Write-Host "Evidencia: $path" }
