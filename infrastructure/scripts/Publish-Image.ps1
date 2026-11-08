#Requires -Version 7.2
[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../config.local.json'),
    [Parameter(Mandatory)][string]$ContextPath,
    [string]$Dockerfile = 'Dockerfile'
)
. "$PSScriptRoot/Common.ps1"
$config = Read-Config $ConfigPath
Assert-AccountConfig $config
Assert-SpendingWindow $config
if ($config.imageTag -eq 'latest' -or $config.imageTag -cnotmatch '^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$') { throw 'Informe imageTag fixa, por exemplo api-<commit>. latest nao e permitido.' }
$context = (Resolve-Path -LiteralPath $ContextPath).Path
if (-not (Test-Path -LiteralPath $context -PathType Container)) { throw 'ContextPath deve ser uma pasta.' }
$dockerfilePath = if ([IO.Path]::IsPathRooted($Dockerfile)) { $Dockerfile } else { Join-Path $context $Dockerfile }
if (-not (Test-Path -LiteralPath $dockerfilePath -PathType Leaf)) { throw "Dockerfile ausente: $dockerfilePath" }
$docker = (Get-Command docker -ErrorAction Stop).Source
$null = Invoke-Tool $docker @('version', '--format', '{{.Server.Version}}')
$null = Assert-Identity $config
$state = Read-State $config
if (-not $state.resources.ContainsKey('repository')) { throw 'Execute Provision.ps1 antes de publicar a imagem.' }
Assert-Owned $config $state $state.resources.repository
$existing = Invoke-Aws $config @('ecr', 'describe-images', '--repository-name', $config.project, '--image-ids', "imageTag=$($config.imageTag)") -NotFoundCodes @('ImageNotFoundException')
if ($existing) { throw 'Tag ja publicada. Para redeploy da mesma imagem, use Deploy.ps1; para nova imagem, escolha nova tag.' }
$registry = "$($config.accountId).dkr.ecr.$($config.region).amazonaws.com"
$taggedUri = "$registry/$($config.project):$($config.imageTag)"
Write-Host 'Construindo imagem Linux amd64...'
$null = Invoke-Tool $docker @('build', '--platform', 'linux/amd64', '--file', $dockerfilePath, '--tag', $taggedUri, $context)
# Credencial temporaria somente em memoria e stdin; nunca em argumentos, arquivos ou logs.
$password = Invoke-Aws $config @('ecr', 'get-login-password') -Raw
try { $null = Invoke-Tool $docker @('login', '--username', 'AWS', '--password-stdin', $registry) -InputText $password }
finally { $password = $null }
try { $null = Invoke-Tool $docker @('push', $taggedUri) }
finally { $null = Invoke-Tool $docker @('logout', $registry) }
$image = (Invoke-Aws $config @('ecr', 'describe-images', '--repository-name', $config.project, '--image-ids', "imageTag=$($config.imageTag)")).imageDetails[0]
$state.image = @{tag = $config.imageTag; digest = $image.imageDigest; uri = "$registry/$($config.project)@$($image.imageDigest)"; timestampUtc = [DateTimeOffset]::UtcNow.ToString('o')}
Save-State $config $state
Write-Json (Join-Path $script:InfraRoot 'evidence/image.json') $state.image
Write-Host "Imagem publicada: $($state.image.uri)"
