# claude-tabs send — Headless-Prompt an existierende Session
# Usage: . .\send.ps1 -SessionId "66966474" -Prompt "ja, Option A"
#
# WICHTIG: Spawnt `claude --resume <id> -p "<prompt>"` im richtigen CWD.
# Caveat: wenn Warp-Tab parallel offen ist, gibt es theoretisch Lock-Risiko auf der JSONL.
# Erster Test sollte mit risikoarmem Prompt (z.B. "echo test") gemacht werden.

param(
    [Parameter(Mandatory = $true)]
    [string]$SessionId,
    [Parameter(Mandatory = $true)]
    [string]$Prompt,
    [int]$TimeoutSeconds = 120,
    [switch]$DryRun
)

$base = "$env:USERPROFILE\.claude\projects"

# Finde die Session (Prefix-Match)
$found = $null
Get-ChildItem -Path $base -Directory | ForEach-Object {
    $dir = $_
    $jsonl = Get-ChildItem -Path $dir.FullName -Filter "$SessionId*.jsonl" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($jsonl) {
        $found = [PSCustomObject]@{
            FullId    = ($jsonl.Name -replace '\.jsonl', '')
            CWD       = ($dir.Name -replace '^C--', 'C:\' -replace '-', '\')
            JsonlPath = $jsonl.FullName
        }
    }
}

if (-not $found) {
    Write-Error "Session not found: $SessionId"
    return
}

Write-Host "Session: $($found.FullId)"
Write-Host "CWD:     $($found.CWD)"
Write-Host "Prompt:  $Prompt"
Write-Host ""

if ($DryRun) {
    Write-Host "[DryRun] Würde ausführen: claude --resume `"$($found.FullId)`" -p `"$Prompt`""
    return
}

# Prüfe ob CWD existiert
if (-not (Test-Path $found.CWD)) {
    Write-Warning "CWD path nicht gefunden, versuche fallback: $($found.CWD)"
}

# Spawn Headless Claude
Push-Location $found.CWD -ErrorAction SilentlyContinue
try {
    $output = & claude --resume $found.FullId -p $Prompt 2>&1
    Write-Host "=== Response ==="
    Write-Host $output
} catch {
    Write-Error "claude --resume failed: $_"
} finally {
    Pop-Location -ErrorAction SilentlyContinue
}
