param(
    [ValidateSet('status','backup','flash-root','boot','restore-android-data')]
    [string]$Action = 'status',
    [switch]$Experimental,
    [switch]$EraseData
)
$ErrorActionPreference = 'Stop'
$phoneArgs = @((Join-Path $PSScriptRoot 'tools/phone.py'), $Action)
if ($Experimental) { $phoneArgs += '--experimental' }
if ($EraseData) { $phoneArgs += '--erase-data' }
& python @phoneArgs
if ($LASTEXITCODE -ne 0) { throw 'Operation interrompue. Lire le diagnostic ci-dessus.' }
