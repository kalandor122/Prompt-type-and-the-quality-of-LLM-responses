# keepawake.ps1 - hold the PC awake while the study runs.
#
# Uses SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED): the system
# will not sleep, but the DISPLAY is still allowed to turn off. That is what you
# want overnight: no power wasted on a monitor nobody is watching, and no lost
# run because Windows suspended the box.
#
# Unlike "powercfg" this touches no power settings, so there is nothing to
# restore. The request is dropped automatically the moment this process dies.
# Close the window, kill it, or crash the machine, and the PC goes back to
# sleeping normally.
#
# NOTE 1: keep this file ASCII-only. Windows PowerShell 5.1 reads a BOM-less
# file as ANSI, and a UTF-8 em-dash decodes there to a character that IS a
# quote -- which silently breaks every string on the line. This file is also
# written with a UTF-8 BOM so PS 5.1 parses it correctly.
#
# NOTE 2: the flag is written as the DECIMAL 2147483649, not the hex 0x80000001.
# PowerShell parses 0x80000000 as a signed Int32 (-2147483648), so the bitwise
# OR comes out negative and refuses to convert to UInt32. Decimal literal,
# explicitly cast, is unambiguous.

$sig = @"
using System;
using System.Runtime.InteropServices;
public class StayAwake {
    [DllImport("kernel32.dll")]
    public static extern uint SetThreadExecutionState(uint esFlags);
}
"@

Add-Type -TypeDefinition $sig -ErrorAction Stop

# ES_CONTINUOUS | ES_SYSTEM_REQUIRED == 0x80000001 == 2147483649
$FLAGS = [uint32]2147483649

try {
    $result = [StayAwake]::SetThreadExecutionState($FLAGS)
} catch {
    Write-Host "keepawake: SetThreadExecutionState THREW: $($_.Exception.Message)"
    exit 1
}

if ($result -eq 0) {
    Write-Host "keepawake: SetThreadExecutionState returned 0 - the PC may still sleep."
    exit 1
}

Write-Host "keepawake: sleep suppressed (display may still turn off). PID $PID"

# Let the .bat find and stop us when the run finishes.
$PID | Out-File -FilePath (Join-Path $PSScriptRoot 'awake.pid') -Encoding ascii

while ($true) {
    # Re-assert every 60s. Harmless, and it survives anything that clears the
    # state without killing us.
    [void][StayAwake]::SetThreadExecutionState($FLAGS)
    Start-Sleep -Seconds 60
}
