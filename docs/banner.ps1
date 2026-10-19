# Renders docs/banner.html to docs/banner-windows.png (2400x800) with headless Chrome or Edge.
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$browser = @("$env:ProgramFiles\Google\Chrome\Application\chrome.exe", "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $browser) { throw 'Needs Chrome or Edge.' }
$page = 'file:///' + ((Join-Path $here 'banner.html') -replace '\\', '/')
& $browser --headless=new --disable-gpu --hide-scrollbars --allow-file-access-from-files --force-device-scale-factor=1 --window-size=2400,800 --virtual-time-budget=3000 "--screenshot=$(Join-Path $here 'banner-windows.png')" $page
