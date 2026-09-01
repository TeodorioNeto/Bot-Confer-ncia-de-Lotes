param(
    [string]$OutputDirectory = "dist/capstone"
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$outputRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot $OutputDirectory))
$expectedRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "dist"))
if (-not $outputRoot.StartsWith($expectedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "O diretorio de saida deve permanecer dentro de dist/."
}

$stagingRoot = Join-Path $outputRoot ".staging"
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
if (Test-Path -LiteralPath $stagingRoot) {
    Remove-Item -LiteralPath $stagingRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stagingRoot | Out-Null

$bots = @(
    @{ Name = "teodorio-orquestrador-capstone-v1"; Entry = "capstone_orchestrator.py"; Extra = @("dispatcher.py") },
    @{ Name = "teodorio-coleta-desktop-v1"; Entry = "bot_coleta_desktop.py"; Extra = @("desktop_app.py") },
    @{ Name = "teodorio-coleta-web-v1"; Entry = "bot_coleta_web.py"; Extra = @("doc.html") },
    @{ Name = "teodorio-consolidacao-v1"; Entry = "bot_consolidacao.py"; Extra = @() },
    @{ Name = "teodorio-classificador-ml-v1"; Entry = "bot_classificador_ml.py"; Extra = @() },
    @{ Name = "teodorio-relatorio-alertas-v1"; Entry = "bot_relatorio_alertas.py"; Extra = @() }
)

foreach ($definition in $bots) {
    $stage = Join-Path $stagingRoot $definition.Name
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $stage "src") | Out-Null
    New-Item -ItemType Directory -Force -Path (Join-Path $stage "dados_entrada") | Out-Null

    Copy-Item -LiteralPath (Join-Path $projectRoot $definition.Entry) -Destination (Join-Path $stage "bot.py")
    Copy-Item -LiteralPath (Join-Path $projectRoot "config.py") -Destination $stage
    Copy-Item -LiteralPath (Join-Path $projectRoot "requirements.txt") -Destination $stage
    Copy-Item -LiteralPath (Join-Path $projectRoot "wait_for_predecessor.py") -Destination $stage
    Copy-Item -Path (Join-Path $projectRoot "src/*.py") -Destination (Join-Path $stage "src")
    Copy-Item -LiteralPath (Join-Path $projectRoot "dados_entrada/inspecao_lotes_dia.xlsx") -Destination (Join-Path $stage "dados_entrada")
    foreach ($extra in $definition.Extra) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $extra) -Destination $stage
    }

    $zipPath = Join-Path $outputRoot ($definition.Name + ".zip")
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -Path (Join-Path $stage "*") -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Host "Criado: $zipPath"
}

Remove-Item -LiteralPath $stagingRoot -Recurse -Force
Write-Host "Pacotes concluídos. O arquivo .env não foi incluído."
