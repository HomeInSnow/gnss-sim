# Post-rename patches for the gnss-sim -> gnss-sim-desktop directory rename.
# Run automatically by D:\workbuddy\rename_gnss_sim_desktop.bat AFTER the
# WorkBuddy app is closed and the folder rename has succeeded.
# Everything here is ASCII-only; paths are fixed strings.

$ErrorActionPreference = 'Continue'
$projOld = 'D:\workbuddy\GNSSSignal\gnss-sim'
$projNew = 'D:\workbuddy\GNSSSignal\gnss-sim-desktop'

function Patch-TextFile([string]$path) {
    if (-not (Test-Path $path)) { return }
    $t = [IO.File]::ReadAllText($path)
    $o = $t
    $t = [regex]::Replace($t, 'GNSSSignal([/\\]+)gnss-sim(?!-desktop)', 'GNSSSignal${1}gnss-sim-desktop')
    $t = [regex]::Replace($t, 'GNSSSignal([/\\]+)PocketSDR(?!-desktop)',  'GNSSSignal${1}pocketSDR-desktop')
    if ($t -ne $o) {
        [IO.File]::WriteAllText($path, $t)
        Write-Host ("patched: " + (Split-Path -Leaf $path))
    }
}

# 1) venv activation scripts + editable-install finder + dist metadata
$v = Join-Path $projNew '.venv\Scripts'
foreach ($f in 'activate','activate.bat','activate.fish','activate.nu','activate.ps1','deactivate.bat') {
    Patch-TextFile (Join-Path $v $f)
}
$sp = Join-Path $projNew '.venv\Lib\site-packages'
Get-ChildItem $sp -Filter '*gps_sim*' -ErrorAction SilentlyContinue | ForEach-Object {
    if ($_.PSIsContainer) {
        Get-ChildItem $_.FullName -Filter '*.json' -Recurse -ErrorAction SilentlyContinue | ForEach-Object { Patch-TextFile $_.FullName }
    }
}
Get-ChildItem $sp -Filter '__editable_*gps_sim*finder*.py' -ErrorAction SilentlyContinue | ForEach-Object { Patch-TextFile $_.FullName }

# 2) migrate harness session store to the new workspace key
$pk = 'C:\Users\Lenovo\.workbuddy\projects'
$srcKey = Join-Path $pk 'd-workbuddy-GNSSSignal-gnss-sim'
$dstKey = Join-Path $pk 'd-workbuddy-GNSSSignal-gnss-sim-desktop'
if (Test-Path $srcKey) {
    if (-not (Test-Path $dstKey)) { New-Item -ItemType Directory -Path $dstKey | Out-Null }
    Copy-Item (Join-Path $srcKey '*') $dstKey -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host 'session store copied to new workspace key'
}

Write-Host 'All post-rename patches done.'
Write-Host 'NOTE: .venv\Scripts\*.exe launchers (pip.exe, pyinstaller.exe) embed the old'
Write-Host '      absolute path and will fail; always use'
Write-Host '      .venv\Scripts\python.exe -m pip / -m PyInstaller instead.'
