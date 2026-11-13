#Requires -Version 7.2
<#
.SYNOPSIS
Executa um experimento da pessoa 3 e salva as evidências em tests/results/<data>-<experimento>-r<n>.

.DESCRIPTION
Roda o k6 (tests/load-test.js) e, enquanto ele gera carga, registra a cada intervalo o estado do
serviço: tasks desejadas, em execução e saudáveis e alvos do target group. No experimento D
encerra uma task no tempo combinado. Ao final exporta métricas do CloudWatch, eventos do ECS,
atividades do Auto Scaling e o histórico dos alarmes, e roda a análise (tests/analysis/analisar.py).

Com -Local usa o ambiente Docker de tests/local (sem AWS) para validar o script e a análise.
Procedimento completo: tests/README.md.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('smoke', 'calibracao', 'A-baseline', 'BC-escalabilidade', 'D-falha')][string]$Experimento,
    [double]$CapacidadeRps = 0,
    [ValidateRange(0, 5000000)][int]$Iteracoes = 0,
    [ValidateRange(1, 20)][int]$Repeticao = 1,
    [string]$Responsavel = '',
    [string]$BaseUrl = '',
    [switch]$Local,
    [ValidateRange(0.01, 1.0)][double]$EscalaTempo = 1.0,
    [ValidateRange(5, 120)][int]$IntervaloColetaSegundos = 10,
    [ValidateRange(10, 3600)][int]$PararTaskAposSegundos = 180,
    [int]$ObservarAposSegundos = -1,
    [ValidateRange(0, 900)][int]$AguardarMetricasSegundos = 180,
    [ValidateRange(5, 600)][int]$ReposicaoLocalSegundos = 20,
    [switch]$K6Docker,
    [string]$K6Imagem = 'grafana/k6:1.0.0',
    [string]$Python = 'python',
    [switch]$IgnorarPrecondicoes,
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../../infrastructure/config.local.json'),
    [string]$Saida = (Join-Path $PSScriptRoot '../results')
)
. (Join-Path $PSScriptRoot '../../infrastructure/scripts/Common.ps1')
$invariante = [Globalization.CultureInfo]::InvariantCulture
$testsDir = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$composeFile = Join-Path $testsDir 'local/docker-compose.yml'

# Objetivo, hipótese e preparação de cada experimento (detalhes em tests/plano-de-testes.md).
$definicoes = @{
    'smoke'             = @{objetivo = 'Verificar /health, /instance e /work no ambiente implantado'; hipotese = 'As três rotas respondem HTTP 200 com JSON válido.'; tasks = 0; autoScaling = $null; observar = 0; capacidade = $false}
    'calibracao'        = @{objetivo = 'Medir a vazão máxima de uma task (CAPACIDADE_RPS)'; hipotese = 'Com a fila sempre ocupada, a vazão se estabiliza no limite de CPU de uma task.'; tasks = 1; autoScaling = $false; observar = 0; capacidade = $false}
    'A-baseline'        = @{objetivo = 'Linha de base: 1 task, carga constante de 50% da capacidade, sem Auto Scaling'; hipotese = 'Vazão igual à oferecida, latência estável, CPU próxima de 50% e nenhum erro.'; tasks = 1; autoScaling = $false; observar = 0; capacidade = $true}
    'BC-escalabilidade' = @{objetivo = 'B: scale-out com carga em degraus (85% e 150% da capacidade de uma task); C: scale-in após reduzir a carga para 20%'; hipotese = 'Em cada degrau a CPU passa de 60%, o alarme dispara e o serviço vai de 1 a 2 e de 2 a 3 tasks; sob a mesma carga, a latência cai com mais tasks. Com carga baixa, volta a 1 task após o alarme de scale-in (cerca de 15 min).'; tasks = 1; autoScaling = $true; observar = 300; capacidade = $true}
    'D-falha'           = @{objetivo = 'Encerrar 1 de 2 tasks sob 80% da capacidade de uma task'; hipotese = 'O ECS inicia uma task substituta e volta a 2 tasks saudáveis; a task restante absorve a carga e os erros ficam restritos ao momento da parada.'; tasks = 2; autoScaling = $false; observar = 120; capacidade = $true}
}
$def = $definicoes[$Experimento]
if ($def.capacidade -and -not ($CapacidadeRps -gt 0)) { throw "Informe -CapacidadeRps (req/s de uma task), medido no experimento calibracao com as mesmas -Iteracoes." }
if ($ObservarAposSegundos -lt 0) { $ObservarAposSegundos = [int][Math]::Ceiling($def.observar * $EscalaTempo) }
if ($Local) { $AguardarMetricasSegundos = 0 }
if (-not $Responsavel) { $Responsavel = try { (& git config user.name 2>$null) } catch { '' }; if (-not $Responsavel) { $Responsavel = $env:USERNAME } }

function Format-Utc { param([DateTimeOffset]$Momento) return $Momento.UtcDateTime.ToString('yyyy-MM-ddTHH:mm:ss.fffZ', $invariante) }
function Hide-AccountId { param([string]$Texto) return [regex]::Replace($Texto, '(?<!\d)(\d{4})\d{4}(\d{4})(?!\d)', '$1****$2') }
function Write-Resultado {
    param([string]$Nome, $Valor)
    $json = ConvertTo-Json -InputObject $Valor -Depth 100
    if (-not $Local) { $json = Hide-AccountId $json }
    $caminho = Join-Path $runDir $Nome
    [IO.Directory]::CreateDirectory((Split-Path $caminho -Parent)) | Out-Null
    [IO.File]::WriteAllText($caminho, $json, [Text.UTF8Encoding]::new($false))
}
function Add-Evento {
    param([DateTimeOffset]$Momento, [string]$Tipo, [string]$Descricao, [hashtable]$Extra = @{})
    $evento = [ordered]@{timestamp_utc = (Format-Utc $Momento); tipo = $Tipo; descricao = $Descricao}
    foreach ($k in $Extra.Keys) { $evento[$k] = $Extra[$k] }
    $script:eventos.Add($evento)
}

# ---------------------------------------------------------------- ambiente local (Docker)
function Invoke-Compose { param([string[]]$Argumentos) return (& docker compose -f $composeFile @Argumentos 2>&1 | Out-String) }
function Get-ReplicasLocais {
    $saida = (& docker compose -f $composeFile ps --all --format json 2>$null | Out-String).Trim()
    if (-not $saida) { return @() }
    $itens = if ($saida.StartsWith('[')) { $saida | ConvertFrom-Json } else { $saida -split "`r?`n" | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json } }
    return @($itens | Where-Object { $_.Service -like 'api-*' } | Sort-Object Service)
}
function Initialize-Local {
    param([int]$Replicas)
    Write-Host "Ambiente local: subindo tests/local (pode construir a imagem da API)..."
    $null = Invoke-Compose @('up', '-d', '--build', '--wait')
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao subir o ambiente local. Verifique o Docker Desktop.' }
    foreach ($i in 1..3) { if ($i -gt $Replicas) { $null = Invoke-Compose @('stop', "api-$i") } }
    # O nginx leva alguns segundos para deixar de enviar pedidos às réplicas paradas.
    $ok = 0; $limite = [DateTimeOffset]::UtcNow.AddSeconds(60)
    while ($ok -lt 20 -and [DateTimeOffset]::UtcNow -lt $limite) {
        try { $null = Invoke-WebRequest -Uri 'http://localhost:8080/health' -TimeoutSec 5; $ok++ } catch { $ok = 0 }
        Start-Sleep -Milliseconds 200
    }
    if ($ok -lt 20) { throw 'O balanceador local não estabilizou em 60 s.' }
}
function Get-EstadoLocal {
    $replicas = Get-ReplicasLocais
    $ativas = @($replicas | Where-Object { $_.State -eq 'running' })
    $linha = [ordered]@{
        desejadas = $script:replicasLocais; em_execucao = $ativas.Count; pendentes = 0
        tasks_saudaveis = @($ativas | Where-Object { $_.Health -eq 'healthy' }).Count
        alvos_saudaveis = ''; alvos_iniciando = ''; alvos_drenando = ''; alvos_nao_saudaveis = ''
        tasks = (@($replicas | ForEach-Object { "$($_.Service):$($_.State):$($_.Health)" }) -join ';')
    }
    return @{linha = $linha; tasks = @($ativas | ForEach-Object { $_.Service })}
}

# ---------------------------------------------------------------- AWS
function Get-EstadoAws {
    $svc = (Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $serviceName)).services[0]
    $arns = @((Invoke-Aws $config @('ecs', 'list-tasks', '--cluster', $config.project, '--service-name', $serviceName)).taskArns)
    $tasks = @()
    if ($arns.Count) { $tasks = @((Invoke-Aws $config (@('ecs', 'describe-tasks', '--cluster', $config.project, '--tasks') + $arns)).tasks) }
    foreach ($t in $tasks) { $null = $script:tasksVistas.Add($t.taskArn) }
    $alvos = @()
    if ($tgArn) { $alvos = @((Invoke-Aws $config @('elbv2', 'describe-target-health', '--target-group-arn', $tgArn)).TargetHealthDescriptions) }
    $estadoAlvo = { param($s) @($alvos | Where-Object { $_.TargetHealth.State -in $s }).Count }
    $saude = { param($t) if ($t.ContainsKey('healthStatus')) { $t.healthStatus } else { 'UNKNOWN' } }
    $linha = [ordered]@{
        desejadas = $svc.desiredCount; em_execucao = $svc.runningCount; pendentes = $svc.pendingCount
        tasks_saudaveis = @($tasks | Where-Object { $_.lastStatus -eq 'RUNNING' -and (& $saude $_) -eq 'HEALTHY' }).Count
        alvos_saudaveis = $(if ($tgArn) { & $estadoAlvo @('healthy') } else { '' })
        alvos_iniciando = $(if ($tgArn) { & $estadoAlvo @('initial') } else { '' })
        alvos_drenando = $(if ($tgArn) { & $estadoAlvo @('draining') } else { '' })
        alvos_nao_saudaveis = $(if ($tgArn) { & $estadoAlvo @('unhealthy', 'unavailable') } else { '' })
        tasks = (@($tasks | ForEach-Object { "$(($_.taskArn -split '/')[-1]):$($_.lastStatus):$(& $saude $_)" }) -join ';')
    }
    return @{linha = $linha; tasks = $tasks}
}
function Get-AlvoParada {
    param($Tasks)
    $candidatas = @($Tasks | Where-Object { $_.lastStatus -eq 'RUNNING' -and $_.ContainsKey('healthStatus') -and $_.healthStatus -eq 'HEALTHY' } | Sort-Object { $_.taskArn })
    if (-not $candidatas.Count) { return $null }
    return $candidatas[0].taskArn
}
function Get-Metrica {
    param([string]$Namespace, [string]$Nome, [string[]]$Dimensoes, [string[]]$Estatisticas, [switch]$Estendida, [DateTimeOffset]$De, [DateTimeOffset]$Ate)
    $arg = @('cloudwatch', 'get-metric-statistics', '--namespace', $Namespace, '--metric-name', $Nome, '--dimensions') + $Dimensoes +
        @('--start-time', $De.ToString('o'), '--end-time', $Ate.ToString('o'), '--period', '60', $(if ($Estendida) { '--extended-statistics' } else { '--statistics' })) + $Estatisticas
    return Invoke-Aws $config $arg
}
function Export-Aws {
    param([DateTimeOffset]$Inicio, [DateTimeOffset]$Fim)
    $de = $Inicio.AddMinutes(-5); $ate = [DateTimeOffset]::UtcNow
    $ecs = @("Name=ClusterName,Value=$($config.project)", "Name=ServiceName,Value=$serviceName")
    foreach ($m in @('CPUUtilization', 'MemoryUtilization')) { Write-Resultado "aws/metricas-ecs-$m.json" (Get-Metrica 'AWS/ECS' $m $ecs @('Average', 'Maximum') -De $de -Ate $ate) }
    if ($tgArn) {
        $lb = "Name=LoadBalancer,Value=$(($state.resources.loadBalancer.arn -split ':loadbalancer/')[1])"
        $tg = "Name=TargetGroup,Value=targetgroup/$(($tgArn -split ':targetgroup/')[1])"
        Write-Resultado 'aws/metricas-alb-HealthyHostCount.json' (Get-Metrica 'AWS/ApplicationELB' 'HealthyHostCount' @($tg, $lb) @('Minimum', 'Maximum') -De $de -Ate $ate)
        Write-Resultado 'aws/metricas-alb-RequestCount.json' (Get-Metrica 'AWS/ApplicationELB' 'RequestCount' @($tg, $lb) @('Sum') -De $de -Ate $ate)
        Write-Resultado 'aws/metricas-alb-HTTPCode_Target_5XX_Count.json' (Get-Metrica 'AWS/ApplicationELB' 'HTTPCode_Target_5XX_Count' @($tg, $lb) @('Sum') -De $de -Ate $ate)
        Write-Resultado 'aws/metricas-alb-HTTPCode_ELB_5XX_Count.json' (Get-Metrica 'AWS/ApplicationELB' 'HTTPCode_ELB_5XX_Count' @($lb) @('Sum') -De $de -Ate $ate)
        Write-Resultado 'aws/metricas-alb-TargetResponseTime-p95.json' (Get-Metrica 'AWS/ApplicationELB' 'TargetResponseTime' @($tg, $lb) @('p95') -Estendida -De $de -Ate $ate)
    }
    $svc = (Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $serviceName)).services[0]
    $eventosEcs = @($svc.events | Where-Object { [DateTimeOffset]$_.createdAt -ge $de })
    Write-Resultado 'aws/ecs-eventos.json' $eventosEcs
    foreach ($e in $eventosEcs) { Add-Evento ([DateTimeOffset]$e.createdAt) 'ecs' $e.message }
    if ($state.resources.ContainsKey('scalableTarget')) {
        $rid = $state.resources.scalableTarget.id
        $atividades = @((Invoke-Aws $config @('application-autoscaling', 'describe-scaling-activities', '--service-namespace', 'ecs', '--resource-id', $rid)).ScalingActivities | Where-Object { [DateTimeOffset]$_.StartTime -ge $de })
        Write-Resultado 'aws/autoscaling-atividades.json' $atividades
        foreach ($a in $atividades) {
            $extra = @{status = $a.StatusCode; causa = $(if ($a.ContainsKey('Cause')) { $a.Cause } else { '' })}
            if ($a.ContainsKey('EndTime')) { $extra.fim_utc = Format-Utc ([DateTimeOffset]$a.EndTime) }
            Add-Evento ([DateTimeOffset]$a.StartTime) 'escalonamento' $a.Description $extra
        }
        $politicas = Invoke-Aws $config @('application-autoscaling', 'describe-scaling-policies', '--service-namespace', 'ecs', '--resource-id', $rid)
        Write-Resultado 'aws/autoscaling-politicas.json' $politicas
        $historico = @()
        foreach ($p in @($politicas.ScalingPolicies)) {
            if (-not $p.ContainsKey('Alarms')) { continue }
            foreach ($alarme in @($p.Alarms)) {
                $h = Invoke-Aws $config @('cloudwatch', 'describe-alarm-history', '--alarm-name', $alarme.AlarmName, '--history-item-type', 'StateUpdate', '--start-date', $de.ToString('o'), '--end-date', $ate.ToString('o'))
                foreach ($item in @($h.AlarmHistoryItems)) {
                    $historico += $item
                    $novo = try { ($item.HistoryData | ConvertFrom-Json -AsHashtable).newState.stateValue } catch { '' }
                    $tipoAlarme = if ($alarme.AlarmName -match 'AlarmHigh') { 'alta' } elseif ($alarme.AlarmName -match 'AlarmLow') { 'baixa' } else { '' }
                    $rotulo = if ($tipoAlarme) { "Alarme de $tipoAlarme (scale-$(if ($tipoAlarme -eq 'alta') { 'out' } else { 'in' }))" } else { "Alarme $($alarme.AlarmName)" }
                    Add-Evento ([DateTimeOffset]$item.Timestamp) 'alarme' "${rotulo}: $($item.HistorySummary)" @{alarme = $alarme.AlarmName; tipo_alarme = $tipoAlarme; estado = $novo}
                }
            }
        }
        Write-Resultado 'aws/alarmes-historico.json' $historico
    }
    if ($script:tasksVistas.Count) {
        $detalhes = @(); $todas = @($script:tasksVistas)
        for ($i = 0; $i -lt $todas.Count; $i += 100) {
            $lote = $todas[$i..([Math]::Min($i + 99, $todas.Count - 1))]
            $detalhes += @((Invoke-Aws $config (@('ecs', 'describe-tasks', '--cluster', $config.project, '--tasks') + @($lote))).tasks)
        }
        Write-Resultado 'aws/tasks.json' $detalhes
    }
}

# ---------------------------------------------------------------- preparação
$script:eventos = [Collections.Generic.List[object]]::new()
$script:tasksVistas = [Collections.Generic.HashSet[string]]::new()
$autoScaling = $null
$identificacao = [ordered]@{}
if ($Local) {
    # Sem Auto Scaling local: B/C rodam com as 3 réplicas (o máximo do plano) para validar carga e análise.
    $script:replicasLocais = switch ($Experimento) { 'smoke' { 3 } 'BC-escalabilidade' { 3 } default { $def.tasks } }
    Initialize-Local $script:replicasLocais
    $identificacao = [ordered]@{ambiente = 'local'; replicas = $script:replicasLocais; observacao = 'Ambiente Docker de tests/local; sem Auto Scaling nem ECS. Serve para validar o script e a análise.'}
    $redeK6 = 'rs-local_default'
} else {
    $config = Read-Config $ConfigPath
    Assert-DeploymentConfig $config
    $identity = Assert-Identity $config
    $state = Read-State $config
    if (-not $state.resources.ContainsKey('service')) { throw 'Serviço ausente no inventário. Execute Deploy.ps1 antes dos experimentos.' }
    Assert-Owned $config $state $state.resources.service
    $serviceName = $state.resources.service.id
    $tgArn = if ($state.resources.ContainsKey('targetGroup')) { $state.resources.targetGroup.arn } else { '' }
    if ($Experimento -in @('BC-escalabilidade', 'D-falha') -and -not $config.useAlb) { throw 'B, C e D exigem ALB (useAlb=true): sem endereço único, o k6 não alcança tasks novas ou substitutas.' }
    if ($state.resources.ContainsKey('scalableTarget')) {
        $pol = Invoke-Aws $config @('application-autoscaling', 'describe-scalable-targets', '--service-namespace', 'ecs', '--resource-ids', $state.resources.scalableTarget.id)
        $alvoEscala = @($pol.ScalableTargets)[0]
        $autoScaling = [ordered]@{min = $alvoEscala.MinCapacity; max = $alvoEscala.MaxCapacity}
        if ($state.ContainsKey('autoScaling')) { foreach ($k in @('targetCpu', 'scaleOutCooldown', 'scaleInCooldown', 'policyName')) { if ($state.autoScaling.ContainsKey($k)) { $autoScaling[$k] = $state.autoScaling[$k] } } }
    }
    $estado = Get-EstadoAws
    $svc = (Invoke-Aws $config @('ecs', 'describe-services', '--cluster', $config.project, '--services', $serviceName)).services[0]
    $problemas = @()
    if ($svc.runningCount -ne $svc.desiredCount -or $svc.pendingCount -ne 0 -or @($svc.deployments).Count -ne 1) { $problemas += "serviço não está estável (desired=$($svc.desiredCount), running=$($svc.runningCount), pending=$($svc.pendingCount), deployments=$(@($svc.deployments).Count))" }
    if ($def.autoScaling -eq $true -and -not $autoScaling) { $problemas += 'Auto Scaling não configurado: execute infrastructure/scripts/Set-AutoScaling.ps1' }
    if ($def.autoScaling -eq $false -and $autoScaling) { $problemas += "Auto Scaling ativo: execute infrastructure/scripts/Remove-AutoScaling.ps1 -DesiredCount $($def.tasks)" }
    $esperadas = if ($def.autoScaling -eq $true -and $autoScaling) { $autoScaling.min } else { $def.tasks }
    if ($esperadas -gt 0 -and $svc.desiredCount -ne $esperadas) { $problemas += "o experimento começa com $esperadas task(s), mas desired=$($svc.desiredCount)" }
    if ($config.useAlb -and $tgArn -and $esperadas -gt 0 -and $estado.linha.alvos_saudaveis -ne $esperadas) { $problemas += "alvos saudáveis no ALB: $($estado.linha.alvos_saudaveis) de $esperadas" }
    if ($problemas.Count) {
        if (-not $IgnorarPrecondicoes) { throw "Pré-condições de $Experimento não atendidas: $($problemas -join '; '). Use -IgnorarPrecondicoes só se a diferença for intencional." }
        Write-Warning "Pré-condições ignoradas: $($problemas -join '; ')"
    }
    if (-not $BaseUrl) {
        $snapshot = Get-DeploymentSnapshot $config $state
        if (@($snapshot.endpoints).Count -eq 0) { throw 'Nenhum endpoint encontrado. Informe -BaseUrl.' }
        $BaseUrl = @($snapshot.endpoints)[0]
    }
    $image = if ($state.ContainsKey('image')) { [ordered]@{tag = $state.image.tag; digest = $state.image.digest} } else { $null }
    $identificacao = [ordered]@{
        ambiente = 'aws'; regiao = $config.region; conta = $identity.Account; cluster = $config.project; servico = $serviceName
        imagem = $image; task_definition = $svc.taskDefinition; alb = [bool]$config.useAlb
        precondicoes_ignoradas = @($problemas)
    }
}
if (-not $BaseUrl) { $BaseUrl = 'http://localhost:8080' }

$inicio = [DateTimeOffset]::UtcNow
$nomeRun = '{0}-{1}-r{2}{3}' -f $inicio.UtcDateTime.ToString('yyyyMMdd-HHmmss', $invariante), $Experimento, $Repeticao, $(if ($Local) { '-local' } else { '' })
$runDir = [IO.Path]::GetFullPath((Join-Path $Saida $nomeRun))
[IO.Directory]::CreateDirectory($runDir) | Out-Null
$metadata = [ordered]@{
    experimento = $Experimento; objetivo = $def.objetivo; hipotese = $def.hipotese; repeticao = $Repeticao; responsavel = $Responsavel
    inicio_utc = (Format-Utc $inicio); fim_utc = $null; identificacao = $identificacao; auto_scaling = $autoScaling
    k6 = [ordered]@{cenario = $Experimento; base_url = $BaseUrl; capacidade_rps = $(if ($CapacidadeRps -gt 0) { $CapacidadeRps } else { $null }); iteracoes = $(if ($Iteracoes) { $Iteracoes } else { $null }); escala_tempo = $EscalaTempo; executor = $(if ($K6Docker -or -not (Get-Command k6 -ErrorAction SilentlyContinue)) { $K6Imagem } else { 'k6 local' }); codigo_saida = $null}
    coleta = [ordered]@{intervalo_s = $IntervaloColetaSegundos; observacao_apos_k6_s = $ObservarAposSegundos; aguardar_metricas_s = $AguardarMetricasSegundos}
    falha = $(if ($Experimento -eq 'D-falha') { [ordered]@{parar_apos_s = [Math]::Round($PararTaskAposSegundos * $EscalaTempo); reposicao_local_s = $(if ($Local) { $ReposicaoLocalSegundos } else { $null })} } else { $null })
}
Write-Resultado 'metadata.json' $metadata
$conclusao = @"
# Conclusão — $Experimento (repetição $Repeticao)

Preencha depois de revisar ``resumo.md`` e os gráficos desta pasta.

## Hipótese

$($def.hipotese)

## Observação real

-

## Limitações

- Estado do serviço amostrado a cada $IntervaloColetaSegundos s; métricas do CloudWatch em períodos de 1 min.

## Próximos ajustes

-
"@
[IO.File]::WriteAllText((Join-Path $runDir 'conclusao.md'), $conclusao, [Text.UTF8Encoding]::new($false))

# ---------------------------------------------------------------- execução
$timeline = Join-Path $runDir 'timeline.csv'
$colunas = @('timestamp_utc', 'decorrido_s', 'desejadas', 'em_execucao', 'pendentes', 'tasks_saudaveis', 'alvos_saudaveis', 'alvos_iniciando', 'alvos_drenando', 'alvos_nao_saudaveis', 'tasks')
[IO.File]::WriteAllText($timeline, ($colunas -join ',') + "`n", [Text.UTF8Encoding]::new($false))

$k6Args = @('run', '--quiet', '--no-color', '--log-output=file=k6-log.txt', '--out', 'csv=fileName=k6-bruto.csv.gz,timeFormat=unix_milli')
$envK6 = [ordered]@{CENARIO = $Experimento; CAPACIDADE_RPS = [string]$CapacidadeRps; ITERACOES = [string]$Iteracoes; ESCALA_TEMPO = $EscalaTempo.ToString($invariante); RESUMO_ARQUIVO = 'resumo-k6.json'}
$usarDocker = $K6Docker -or -not (Get-Command k6 -ErrorAction SilentlyContinue)
$urlK6 = if ($Local -and $usarDocker) { 'http://lb' } else { $BaseUrl }
$envK6.BASE_URL = $urlK6
foreach ($k in $envK6.Keys) { $k6Args += @('-e', "$k=$($envK6[$k])") }
$start = [Diagnostics.ProcessStartInfo]::new()
$start.UseShellExecute = $false
if ($usarDocker) {
    $start.FileName = (Get-Command docker -ErrorAction Stop).Source
    $dockerArgs = @('run', '--rm', '-v', "${runDir}:/resultados", '-v', "${testsDir}:/testes:ro", '-w', '/resultados')
    # No Linux/macOS o container precisa do mesmo uid para gravar na pasta de resultados.
    if (-not $IsWindows) { $dockerArgs += @('--user', "$(& id -u):$(& id -g)") }
    if ($Local) { $dockerArgs += @('--network', $redeK6) }
    foreach ($a in ($dockerArgs + @($K6Imagem) + $k6Args + @('/testes/load-test.js'))) { $start.ArgumentList.Add($a) }
} else {
    $start.FileName = (Get-Command k6).Source
    $start.WorkingDirectory = $runDir
    foreach ($a in ($k6Args + @((Join-Path $testsDir 'load-test.js')))) { $start.ArgumentList.Add($a) }
}

Write-Host "Experimento $Experimento (repetição $Repeticao) contra $BaseUrl. Resultados em $runDir"
$k6 = [Diagnostics.Process]::Start($start)
Add-Evento ([DateTimeOffset]::UtcNow) 'k6_inicio' "k6 iniciado ($Experimento)"
$pararEm = if ($Experimento -eq 'D-falha') { $inicio.AddSeconds([Math]::Round($PararTaskAposSegundos * $EscalaTempo)) } else { $null }
$parada = $null; $reposta = $false; $fimK6 = $null; $fimObservacao = $null; $ultimoEstado = $null
try {
    while ($true) {
        $agora = [DateTimeOffset]::UtcNow
        try {
            $ultimoEstado = if ($Local) { Get-EstadoLocal } else { Get-EstadoAws }
            $valores = @((Format-Utc $agora), [Math]::Round(($agora - $inicio).TotalSeconds, 1).ToString($invariante)) + @($ultimoEstado.linha.Values | ForEach-Object { "$_" })
            [IO.File]::AppendAllText($timeline, ($valores -join ',') + "`n", [Text.UTF8Encoding]::new($false))
            $l = $ultimoEstado.linha
            Write-Host ("[{0,6:N0} s] desejadas={1} em execução={2} saudáveis={3} alvos ALB saudáveis={4}" -f ($agora - $inicio).TotalSeconds, $l.desejadas, $l.em_execucao, $l.tasks_saudaveis, $l.alvos_saudaveis)
        } catch { Write-Warning "Coleta falhou neste ciclo: $($_.Exception.Message)" }
        if ($pararEm -and -not $parada -and $agora -ge $pararEm -and $ultimoEstado) {
            # O momento registrado é o do pedido de parada, antes de o comando retornar.
            if ($Local) {
                $script:alvoLocal = @($ultimoEstado.tasks)[0]
                if ($script:alvoLocal) {
                    $parada = [DateTimeOffset]::UtcNow
                    # SIGTERM e até 10 s para concluir pedidos em andamento, como o stop-task do ECS.
                    $null = Invoke-Compose @('stop', '-t', '10', $script:alvoLocal)
                    Add-Evento $parada 'stop_task' "Réplica $($script:alvoLocal) encerrada (docker compose stop)" @{task = $script:alvoLocal; concluido_utc = (Format-Utc ([DateTimeOffset]::UtcNow))}
                }
            } else {
                $alvo = Get-AlvoParada $ultimoEstado.tasks
                if ($alvo) {
                    $parada = [DateTimeOffset]::UtcNow
                    $null = Invoke-Aws $config @('ecs', 'stop-task', '--cluster', $config.project, '--task', $alvo, '--reason', "Experimento D (falha controlada), repeticao $Repeticao")
                    Add-Evento $parada 'stop_task' "Task $(($alvo -split '/')[-1]) encerrada com stop-task" @{task = ($alvo -split '/')[-1]; concluido_utc = (Format-Utc ([DateTimeOffset]::UtcNow))}
                } else { Write-Warning 'Nenhuma task saudável para encerrar neste ciclo; nova tentativa no próximo.' }
            }
            if ($parada) { Write-Host "Task encerrada em $(Format-Utc $parada)." }
        }
        if ($Local -and $parada -and -not $reposta -and $agora -ge $parada.AddSeconds($ReposicaoLocalSegundos)) {
            # `start` não espera o health check: a coleta continua registrando a recuperação.
            $momento = [DateTimeOffset]::UtcNow
            $null = Invoke-Compose @('start', $script:alvoLocal)
            $reposta = $true
            Add-Evento $momento 'start_replica' "Réplica $($script:alvoLocal) reiniciada após $ReposicaoLocalSegundos s (no ECS a substituição é automática)"
        }
        if ($k6.HasExited -and -not $fimK6) {
            $fimK6 = [DateTimeOffset]::UtcNow
            Add-Evento $fimK6 'k6_fim' "k6 terminou (código $($k6.ExitCode))"
            $fimObservacao = $fimK6.AddSeconds($ObservarAposSegundos)
            if ($ObservarAposSegundos -gt 0) { Write-Host "k6 terminou; observando o serviço por mais $ObservarAposSegundos s." }
        }
        if ($fimK6 -and [DateTimeOffset]::UtcNow -ge $fimObservacao) { break }
        # Espera até o próximo ciclo; se o k6 terminar antes, coleta logo o estado final.
        $restante = [int]($IntervaloColetaSegundos * 1000 - ([DateTimeOffset]::UtcNow - $agora).TotalMilliseconds)
        if ($restante -gt 0) { if ($k6.HasExited) { Start-Sleep -Milliseconds $restante } else { $null = $k6.WaitForExit($restante) } }
    }
} finally {
    if (-not $k6.HasExited) { $k6.Kill($true); Write-Warning 'k6 interrompido.' }
}
$metadata.k6.codigo_saida = $k6.ExitCode
$fim = [DateTimeOffset]::UtcNow
$metadata.fim_utc = Format-Utc $fim

if (-not $Local) {
    if ($AguardarMetricasSegundos -gt 0) { Write-Host "Aguardando $AguardarMetricasSegundos s para o CloudWatch consolidar as métricas..."; Start-Sleep -Seconds $AguardarMetricasSegundos }
    try { Export-Aws $inicio $fim } catch { Write-Warning "Exportação AWS incompleta: $($_.Exception.Message)"; $metadata.exportacao_erro = $_.Exception.Message }
}
Write-Resultado 'eventos.json' @($script:eventos | Sort-Object { $_.timestamp_utc })
Write-Resultado 'metadata.json' $metadata

$analise = Join-Path $testsDir 'analysis/analisar.py'
try {
    & $Python $analise analisar $runDir
    if ($LASTEXITCODE -ne 0) { throw "código $LASTEXITCODE" }
} catch { Write-Warning "Análise não executada ($($_.Exception.Message)). Rode depois: $Python tests/analysis/analisar.py analisar `"$runDir`"" }
Write-Host "Concluído. Evidências em $runDir. Revise e preencha conclusao.md antes de versionar."
if ($k6.ExitCode -notin @(0)) { Write-Warning "k6 terminou com código $($k6.ExitCode) (99 = limites do cenário smoke violados). Consulte k6-log.txt." }
