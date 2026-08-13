# claude-tabs list — enumeriert alle Claude-Code-Sessions mit Letzter-Aktivität
# Usage: . .\list.ps1 [-MaxResults 25] [-OnlyActive]

param(
    [int]$MaxResults = 25,
    [switch]$OnlyActive  # nur Sessions mit Aktivität in letzten 60 Min
)

$base = "$env:USERPROFILE\.claude\projects"
if (-not (Test-Path $base)) {
    Write-Error "Claude projects dir not found: $base"
    return
}

$results = Get-ChildItem -Path $base -Directory | ForEach-Object {
    $dir = $_
    $latest = Get-ChildItem -Path $dir.FullName -Filter "*.jsonl" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) {
        $mins = [math]::Round((New-TimeSpan -Start $latest.LastWriteTime -End (Get-Date)).TotalMinutes, 1)
        [PSCustomObject]@{
            Project   = ($dir.Name -replace 'C--Users-Legion-', '' -replace 'Documents-', '')
            MinAgo    = $mins
            SizeKB    = [math]::Round($latest.Length / 1024, 0)
            SessionId = ($latest.Name -replace '\.jsonl', '').Substring(0, 8)
            FullId    = ($latest.Name -replace '\.jsonl', '')
            CWD       = ($dir.Name -replace '^C--', 'C:\' -replace '-', '\')
            JsonlPath = $latest.FullName
        }
    }
} | Sort-Object MinAgo

if ($OnlyActive) {
    $results = $results | Where-Object { $_.MinAgo -lt 60 }
}

$results | Select-Object -First $MaxResults
