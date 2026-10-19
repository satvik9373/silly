# Reproducible, non-installing Silly release validation.
# It never invokes build.ps1, registers startup, launches the GUI, or changes
# an installed copy. Supply a new/empty temporary output directory.
param(
  [Parameter(Mandatory = $true)] [string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$out = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path $out) {
  if ((Get-ChildItem -LiteralPath $out -Force | Measure-Object).Count -gt 0) {
    throw "OutputDirectory must be new or empty: $out"
  }
} else {
  New-Item -ItemType Directory -Force $out | Out-Null
}

Push-Location $root
try {
  # The installer copies the Python brain beside Silly.exe. Keep the release
  # check aware of every direct runtime import without invoking build.ps1.
  $installer = Get-Content (Join-Path $root 'build.ps1') -Raw
  foreach ($helper in @('action_engine.py', 'ai_provider_router.py', 'openai_siwc.py', 'winctl.py')) {
    if (-not $installer.Contains("Copy-Item $helper")) { throw "Installer does not stage required Python helper: $helper" }
  }
  py -3 -m pytest -q
  if ($LASTEXITCODE) { throw 'Python tests failed.' }
  py -3 silly.py --selftest
  if ($LASTEXITCODE) { throw 'Python self-test failed.' }
  dotnet build win\Atticus -c Release --nologo -v minimal
  if ($LASTEXITCODE) { throw '.NET build failed.' }
  & (Join-Path $root 'win\Atticus\bin\Release\net10.0-windows10.0.19041.0\Silly.exe') --selftest
  if ($LASTEXITCODE) { throw 'Native self-test failed.' }
  dotnet publish win\Atticus -c Release -r win-x64 --self-contained -p:DebugType=none -o $out --nologo -v minimal
  if ($LASTEXITCODE) { throw 'Publish failed.' }
  # The WebView UI is deliberately local and includes bundled component assets.
  Copy-Item (Join-Path $root 'ui') (Join-Path $out 'ui') -Recurse -Force
  if (-not (Test-Path (Join-Path $out 'ui\vendor\webawesome\webawesome.loader.js'))) { throw 'Bundled Web Awesome assets are missing from publish output.' }
  if (-not (Test-Path (Join-Path $out 'ui\assets\fonts\Satoshi-Fontshare-EULA.txt'))) { throw 'Satoshi font attribution is missing from publish output.' }
  & (Join-Path $out 'Silly.exe') --selftest
  if ($LASTEXITCODE) { throw 'Published native self-test failed.' }
  git diff --check
  if ($LASTEXITCODE) { throw 'git diff --check failed.' }
  Write-Host "Silly release validation passed: $out"
}
finally {
  Pop-Location
}
