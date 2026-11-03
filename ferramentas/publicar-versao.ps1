# Publishes the current Ilha cursors version as a GitHub release (same format as relogio-mond, ilha and clave).
# Before: bump the version in versao.json, generate.py (VERSION) and the top of CHANGELOG.md, run
# `python generate.py`, commit and push. Needs gh logged in. Publishing is Felipe's decision.
#
# The package is ilha-cursors-<version>.zip: the generated cursors (build\black, build\white, build\manifest.json)
# plus install.py / install.bat, so installing it needs only Python (no numpy, no Pillow).
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\ferramentas\publicar-versao.ps1
#   powershell -ExecutionPolicy Bypass -File .\ferramentas\publicar-versao.ps1 -SoGerar <folder>
#     (only builds the zip in the folder, without git and without gh)
param([string]$SoGerar = '')
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

function Rodar([string]$exe, [string[]]$argumentos) {
    # Windows PowerShell 5.1 turns any stderr line into a fatal error under 'Stop', even when the command worked.
    $ErrorActionPreference = 'Continue'
    $saida = & $exe @argumentos 2>&1 | ForEach-Object { "$_" }
    return [pscustomobject]@{ codigo = $LASTEXITCODE; saida = (($saida -join "`n").Trim()) }
}

$info = [IO.File]::ReadAllText((Join-Path $raiz 'versao.json')) | ConvertFrom-Json
$versao = $info.versao
$repo = $info.repositorio

# the version has to be the same in every place it lives
if ([IO.File]::ReadAllText((Join-Path $raiz 'generate.py')) -notmatch 'VERSION = "([0-9.]+)"') { throw 'No VERSION in generate.py.' }
if ($Matches[1] -ne $versao) { throw "versao.json says $versao and generate.py says $($Matches[1])." }
$manifestFile = Join-Path $raiz 'build\manifest.json'
if (-not (Test-Path $manifestFile)) { throw 'build\manifest.json is missing. Run: python generate.py' }
$construida = ([IO.File]::ReadAllText($manifestFile) | ConvertFrom-Json).version
if ($construida -ne $versao) { throw "build\ is $construida but the version is $versao. Run: python generate.py" }
$changelog = [IO.File]::ReadAllText((Join-Path $raiz 'CHANGELOG.md'))
$linhas = $changelog -split "`r?`n"
$topo = $linhas | Where-Object { $_ -match '^## ' } | Select-Object -First 1
if (-not $topo -or $topo -notmatch '^## ([0-9]+\.[0-9]+\.[0-9]+)') { throw 'CHANGELOG.md has no "## X.Y.Z" section at the top.' }
if ($Matches[1] -ne $versao) { throw "versao.json says $versao and the top of CHANGELOG.md says $($Matches[1])." }
Write-Host "Version $versao"

$inicio = [array]::IndexOf($linhas, $topo)
$notas = @()
for ($i = $inicio + 1; $i -lt $linhas.Length; $i++) { if ($linhas[$i] -match '^## ') { break }; $notas += $linhas[$i] }
$textoNotas = ($notas -join "`n").Trim()
if (-not $textoNotas) { throw "The $versao section of CHANGELOG.md is empty." }

$local = ''
if (-not $SoGerar) {
    if ((Rodar git @('status', '--porcelain')).saida) { throw 'There are uncommitted changes. Commit before publishing.' }
    if ((Rodar git @('fetch', '-q', 'origin')).codigo -ne 0) { throw 'Could not reach GitHub (git fetch).' }
    $local = (Rodar git @('rev-parse', 'HEAD')).saida
    $r = Rodar git @('rev-parse', '@{u}')
    if ($r.codigo -ne 0) { throw 'This branch is not linked to GitHub. Run: git push -u origin master' }
    if ($local -ne $r.saida) { throw 'The current commit is not on GitHub yet (git push) or is behind it.' }
    if ((Rodar gh @('release', 'view', "v$versao", '--repo', $repo)).codigo -eq 0) { throw "Release v$versao already exists." }
}

$trabalho = if ($SoGerar) { [IO.Path]::GetFullPath($SoGerar) } else { Join-Path $env:TEMP "ilha-cursors-release-$versao" }
$pasta = Join-Path $trabalho 'ilha-cursors'
if (Test-Path $pasta) { Remove-Item $pasta -Recurse -Force }
New-Item -ItemType Directory -Force $pasta | Out-Null
$build = Join-Path $pasta 'build'
New-Item -ItemType Directory -Force $build | Out-Null
foreach ($v in @('black', 'white')) { Copy-Item (Join-Path $raiz "build\$v") (Join-Path $build $v) -Recurse }
Copy-Item $manifestFile $build
foreach ($f in @('install.py', 'install.bat', 'README.md', 'LICENSE', 'CHANGELOG.md', 'versao.json')) { Copy-Item (Join-Path $raiz $f) $pasta }

$zip = Join-Path $trabalho "ilha-cursors-$versao.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Add-Type -AssemblyName System.IO.Compression.FileSystem
# entry by entry: ZipFile.CreateFromDirectory in Windows PowerShell 5.1 writes the names with backslashes
$archive = [IO.Compression.ZipFile]::Open($zip, 'Create')
try {
    $prefixo = (Resolve-Path $pasta).Path.TrimEnd('\').Length + 1
    foreach ($file in Get-ChildItem $pasta -Recurse -File) {
        $nome = 'ilha-cursors/' + $file.FullName.Substring($prefixo).Replace('\', '/')
        [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $file.FullName, $nome, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally { $archive.Dispose() }
Write-Host ("Package: {0} ({1:N1} MB)" -f $zip, ((Get-Item $zip).Length / 1MB))
if ($SoGerar) { return }

$arqNotas = Join-Path $trabalho 'notas.md'
[IO.File]::WriteAllText($arqNotas, $textoNotas, [Text.UTF8Encoding]::new($false))
Write-Host "Publishing v$versao to $repo"
$r = Rodar gh @('release', 'create', "v$versao", $zip, '--repo', $repo, '--title', "Ilha Cursors $versao", '--notes-file', $arqNotas, '--target', $local)
if ($r.codigo -ne 0) { throw "gh did not create the release: $($r.saida)" }
Write-Host $r.saida
