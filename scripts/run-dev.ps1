# Builds and launches an isolated Silly development copy. It never invokes the
# installer, writes startup registration, or changes the installed app.
param([switch]$Keep, [string]$Demo)

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$run = Join-Path $env:TEMP ('silly-dev-' + [guid]::NewGuid())
$out = Join-Path $run 'app'
$config = Join-Path $run 'config'
$venv = Join-Path $run 'venv'
$py = $null
foreach ($candidate in @(@('py', '-3.13'), @('py', '-3.12'), @('py', '-3.11'), @('python'))) {
  try { $version = & $candidate[0] $candidate[1..9] -c 'import sys; print(sys.version_info >= (3, 11))' 2>$null; if ($version -eq 'True') { $py = $candidate; break } } catch {}
}
if (-not $py) { throw 'Silly development run needs Python 3.11 or later.' }
& $py[0] $py[1..9] -m venv $venv
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install -q --disable-pip-version-check -r (Join-Path $root 'requirements.txt')
if ($LASTEXITCODE) { throw 'Silly development Python dependencies could not be installed.' }

Push-Location $root
try {
  dotnet publish win\Atticus -c Debug -r win-x64 --self-contained -p:DebugType=none -o $out --nologo -v minimal
  if ($LASTEXITCODE) { throw 'Silly development publish failed.' }
  New-Item -ItemType Directory -Force (Join-Path $out 'ui'), $config | Out-Null
  Copy-Item (Join-Path $root 'ui\*') (Join-Path $out 'ui') -Recurse -Force
  $env:SILLY_DEVELOPMENT = '1'
  $env:SILLY_DIR = $config
  $env:SILLY_PYTHON = $python
  $env:SILLY_SCRIPT = Join-Path $root 'silly.py'
  if ($Demo) { $env:SILLY_DEMO = $Demo } else { Remove-Item Env:SILLY_DEMO -ErrorAction SilentlyContinue }
  Start-Process (Join-Path $out 'Silly.exe')
  Write-Host "Silly development build started from $out"
  Write-Host 'No installer or login-startup registration was used. Python dependencies are isolated under this temporary development run.'
  Write-Host 'Hold Ctrl+Alt+Space, speak, then release.'
  if ($Keep) { Write-Host "Development state is in $run" }
}
finally { Pop-Location }
