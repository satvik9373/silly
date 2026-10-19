# Silly installer. Set SILLY_REPOSITORY to the Silly repository URL before running.
# Checks the PC, downloads Silly to %USERPROFILE%\.silly, builds it, and opens it.
$ErrorActionPreference = 'Stop'
$src = Join-Path $env:USERPROFILE '.silly'
$repo = $env:SILLY_REPOSITORY
function Need($cmd, $id, $what) {
  if (Get-Command $cmd -ErrorAction SilentlyContinue) { return }
  Write-Host "Installing $what…"
  winget install --id $id -e --silent --accept-package-agreements --accept-source-agreements | Out-Null
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { throw "Could not install $what. Install it, then run this again." }
}
Need git Git.Git 'Git for Windows'
if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) { Need py Python.Python.3.12 'Python 3.12' }
if (Test-Path "$src\.git") { git -C $src pull -q --ff-only } elseif ($repo) { git clone -q $repo $src } else { throw 'Set SILLY_REPOSITORY to the Silly repository URL before running this installer.' }
& powershell -NoProfile -ExecutionPolicy Bypass -File "$src\build.ps1"
