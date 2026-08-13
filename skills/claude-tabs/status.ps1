# claude-tabs status — Tail einer Session parsen + Status klassifizieren
# Usage: . .\status.ps1 -ProjectPattern "Playbook01"  oder  -SessionId "66966474"

param(
    [string]$ProjectPattern = $null,
    [string]$SessionId = $null,
    [int]$TailLines = 30
)

$base = "$env:USERPROFILE\.claude\projects"

# Finde matchende Session-Files
$files = Get-ChildItem -Path $base -Directory | ForEach-Object {
    $dir = $_
    if ($ProjectPattern -and $dir.Name -notlike "*$ProjectPattern*") { return }
    $jsonls = Get-ChildItem -Path $dir.FullName -Filter "*.jsonl" -ErrorAction SilentlyContinue
    if ($SessionId) {
        $jsonls = $jsonls | Where-Object { $_.Name -like "$SessionId*" }
    } else {
        $jsonls = $jsonls | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    }
    foreach ($f in $jsonls) {
        [PSCustomObject]@{
            Project = $dir.Name
            File    = $f
        }
    }
} | Where-Object { $_ -ne $null }

foreach ($entry in $files) {
    $file = $entry.File
    Write-Host "=== $($entry.Project) — $($file.Name) ==="
    Write-Host "Last mod: $($file.LastWriteTime)"

    $allLines = Get-Content $file.FullName
    $total = $allLines.Count
    Write-Host "Total events: $total"

    $lastUser = $null
    $lastAssist = $null
    $lastTool = $null
    $hasError = $false

    for ($i = $total - 1; $i -ge [math]::Max(0, $total - $TailLines); $i--) {
        try {
            $obj = $allLines[$i] | ConvertFrom-Json
            if ($obj.type -eq 'user' -and -not $lastUser) { $lastUser = $obj }
            if ($obj.type -eq 'assistant' -and -not $lastAssist) { $lastAssist = $obj }
            if ($obj.message.content[0].type -eq 'tool_use' -and -not $lastTool) { $lastTool = $obj }
            if ($obj.message.content[0].is_error) { $hasError = $true }
        } catch { }
    }

    # Status-Klassifizierung
    $status = "unknown"
    if ($hasError) { $status = "🔴 error" }
    elseif ($lastAssist -and $lastAssist.message.stop_reason -eq 'end_turn') { $status = "🟡 waiting-for-user" }
    elseif ($lastTool) { $status = "🟢 executing-tool" }
    else { $status = "🟢 active" }

    Write-Host "Status: $status"

    if ($lastUser) {
        $uc = if ($lastUser.message.content -is [string]) { $lastUser.message.content } else { ($lastUser.message.content | ConvertTo-Json -Compress -Depth 3) }
        Write-Host "[USER LAST] $($uc.Substring(0, [math]::Min(200, $uc.Length)))"
    }
    if ($lastAssist) {
        $ac = if ($lastAssist.message.content -is [string]) { $lastAssist.message.content } else { ($lastAssist.message.content | ConvertTo-Json -Compress -Depth 3) }
        Write-Host "[ASSIST LAST] $($ac.Substring(0, [math]::Min(400, $ac.Length)))"
    }
    Write-Host ""
}
