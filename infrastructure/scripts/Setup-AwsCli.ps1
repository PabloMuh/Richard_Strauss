#Requires -Version 7.2
[CmdletBinding()]
param()
. "$PSScriptRoot/Common.ps1"
try {
    $aws = Get-AwsExecutable
    $version = Invoke-Tool $aws @('--version')
    if ($version -match '^aws-cli/2\.') { Write-Host $version.Trim(); return }
} catch { Write-Host 'Instalando AWS CLI v2 pelo instalador oficial...' }
if (-not $IsWindows) { throw 'Este instalador e para Windows. Consulte a documentacao AWS para seu sistema.' }
$installer = Join-Path ([IO.Path]::GetTempPath()) ('AWSCLIV2-' + [guid]::NewGuid().ToString() + '.msi')
try {
    Invoke-WebRequest -Uri 'https://awscli.amazonaws.com/AWSCLIV2-User.msi' -OutFile $installer
    $signature = Get-AuthenticodeSignature -LiteralPath $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Amazon') { throw 'Assinatura do instalador AWS invalida. Instalacao cancelada.' }
    $installLog = Join-Path ([IO.Path]::GetTempPath()) 'richard-strauss-awscli-install.log'
    $process = Start-Process -FilePath 'msiexec.exe' -ArgumentList @('/i', ('"' + $installer + '"'), '/qn', '/norestart', '/L*v', ('"' + $installLog + '"')) -Wait -PassThru -WindowStyle Hidden
    if ($process.ExitCode -notin @(0, 3010)) { throw "Instalacao por usuario falhou (codigo $($process.ExitCode)). Consulte $installLog." }
    $aws = Get-AwsExecutable
    $version = Invoke-Tool $aws @('--version')
    if ($version -notmatch '^aws-cli/2\.') { throw 'AWS CLI v2 nao encontrada apos a instalacao.' }
    Write-Host $version.Trim()
    Write-Host 'Abra um novo terminal. Nenhum perfil ou credencial foi alterado.'
} finally { if (Test-Path -LiteralPath $installer) { Remove-Item -LiteralPath $installer } }
