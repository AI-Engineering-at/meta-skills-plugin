<#
.SYNOPSIS
    Auto-Update für meta-skills Plugin-Cache aus Source via Junction.

.DESCRIPTION
    Detects ob Source neuer ist als Cache, refresht Cache wenn ja.
    Nach Source-Edit zu meta-skills wird Cache automatisch in sync gebracht.
    Verhindert E207-Pattern (Plugin-Cache stale über Wochen ohne Detection).

    Reihenfolge:
    1. Get plugin.json version aus Source
    2. Get plugin.json version aus Cache (wenn vorhanden)
    3. Wenn Versionen unterscheiden ODER --force: Cache neu befüllen
    4. Wenn Source-Files neuer als Cache: refresh
    5. Verify durch JSON-Parse + hooks.json count

.PARAMETER Force
    Force-Refresh auch wenn Versionen gleich (z.B. nach inkrementellem Edit)

.PARAMETER Verbose
    Detail-Output

.PARAMETER Source
    Override Source-Path (default: ~/Documents/phantom-ai/meta-skills)

.PARAMETER Cache
    Override Cache-Path (default: ~/.claude/plugins/cache/meta-skills-local/meta-skills/<version>/)

.EXAMPLE
    .\plugin-auto-update.ps1
    Refresht Cache nur wenn Source neuer ist.

.EXAMPLE
    .\plugin-auto-update.ps1 -Force -Verbose
    Force-Refresh mit Detail-Output.

.NOTES
    Anlass: E207 (Plugin-Cache stale 28 Tage).
    TaskScheduler-Integration: siehe README oder am Ende dieses Files.
#>

param(
    [switch]$Force,
    [switch]$VerboseOutput,
    [string]$Source = "$env:USERPROFILE\Documents\phantom-ai\meta-skills",
    [string]$Cache = $null
)

$ErrorActionPreference = "Stop"

function Write-Verbose-If([string]$msg) {
    if ($VerboseOutput) { Write-Host "[plugin-auto-update] $msg" }
}

function Get-PluginVersion([string]$path) {
    $pjson = Join-Path $path ".claude-plugin\plugin.json"
    if (-not (Test-Path $pjson)) { return $null }
    try {
        $j = [System.IO.File]::ReadAllText($pjson) | ConvertFrom-Json
        return $j.version
    } catch {
        return $null
    }
}

function Get-NewestFileMtime([string]$path) {
    if (-not (Test-Path $path)) { return [DateTime]::MinValue }
    $newest = Get-ChildItem -Path $path -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notmatch '\\__pycache__\\|\\.git\\|\\.ruff_cache\\' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if ($null -eq $newest) { return [DateTime]::MinValue }
    return $newest.LastWriteTime
}

# Resolve Cache path
if (-not $Cache) {
    $src_version = Get-PluginVersion $Source
    if (-not $src_version) {
        Write-Error "Source plugin.json missing or unparseable at $Source"
        exit 3
    }
    # Use existing cache-version-dir (might differ from src_version!)
    $cache_root = "$env:USERPROFILE\.claude\plugins\cache\meta-skills-local\meta-skills"
    $cache_dirs = Get-ChildItem $cache_root -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -notmatch "backup" } |
        Sort-Object LastWriteTime -Descending
    if ($cache_dirs) {
        $Cache = $cache_dirs[0].FullName
        Write-Verbose-If "Using existing cache-version-dir: $($cache_dirs[0].Name)"
    } else {
        $Cache = Join-Path $cache_root $src_version
        Write-Verbose-If "No cache-version-dir, creating: $src_version"
    }
}

Write-Verbose-If "Source: $Source"
Write-Verbose-If "Cache:  $Cache"

# Pre-conditions
if (-not (Test-Path $Source)) {
    Write-Error "Source path does not exist: $Source"
    exit 3
}

$src_version = Get-PluginVersion $Source
$cache_version = Get-PluginVersion $Cache
$src_mtime = Get-NewestFileMtime $Source
$cache_mtime = if (Test-Path $Cache) { Get-NewestFileMtime $Cache } else { [DateTime]::MinValue }

Write-Verbose-If "Source version: $src_version (newest file mtime: $src_mtime)"
Write-Verbose-If "Cache version:  $cache_version (newest file mtime: $cache_mtime)"

# Decision: refresh or not
$refresh_needed = $Force -or ($src_version -ne $cache_version) -or ($src_mtime -gt $cache_mtime)

if (-not $refresh_needed) {
    $result = @{
        action = "skip"
        reason = "Cache up-to-date (version=$cache_version, mtime=$cache_mtime)"
        source_version = $src_version
        cache_version = $cache_version
        source_mtime = $src_mtime.ToString("o")
        cache_mtime = $cache_mtime.ToString("o")
    }
    Write-Output ($result | ConvertTo-Json)
    exit 0
}

# Backup before refresh
$backup_path = "$Cache.backup-$(Get-Date -Format 'yyyy-MM-ddTHHmmss')"
if (Test-Path $Cache) {
    Write-Verbose-If "Backup: $Cache -> $backup_path"
    Copy-Item -Path $Cache -Destination $backup_path -Recurse -Force
}

# Refresh: copy source-Subdirs into cache
$subdirs_to_sync = @(".claude-plugin", "hooks", "skills", "commands", "agents", "scripts", "plans", "oversight", "self-improving")
$copied_counts = @{}
foreach ($d in $subdirs_to_sync) {
    $sp = Join-Path $Source $d
    $tp = Join-Path $Cache $d
    if (Test-Path $sp) {
        if (Test-Path $tp) { Remove-Item -Path $tp -Recurse -Force }
        Copy-Item -Path $sp -Destination $tp -Recurse -Force -Exclude @("__pycache__", "*.pyc")
        $tc = (Get-ChildItem $tp -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
        $copied_counts[$d] = $tc
        Write-Verbose-If "  $d : $tc files"
    }
}

# Verify
$new_version = Get-PluginVersion $Cache
$hooks_json = Join-Path $Cache "hooks\hooks.json"
$hook_event_count = 0
if (Test-Path $hooks_json) {
    $hj = [System.IO.File]::ReadAllText($hooks_json) | ConvertFrom-Json
    $hook_event_count = ($hj.hooks.PSObject.Properties.Name | Measure-Object).Count
}
$python_hook_count = (Get-ChildItem (Join-Path $Cache "hooks") -Filter "*.py" -ErrorAction SilentlyContinue | Measure-Object).Count

# Cleanup old backups (keep last 5)
$all_backups = Get-ChildItem (Split-Path $Cache) -Directory |
    Where-Object { $_.Name -match "backup" } |
    Sort-Object LastWriteTime -Descending
if ($all_backups.Count -gt 5) {
    $all_backups | Select-Object -Skip 5 | ForEach-Object {
        Write-Verbose-If "Cleanup old backup: $($_.Name)"
        Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$result = @{
    action = "refresh"
    source_version = $src_version
    cache_version_after = $new_version
    backup_path = $backup_path
    subdirs_synced = $copied_counts
    hooks_json_events = $hook_event_count
    python_hooks = $python_hook_count
    timestamp = (Get-Date -Format "o")
}
Write-Output ($result | ConvertTo-Json -Depth 4)
exit 0

<#
TaskScheduler-Integration (einmalig auf .91):

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Users\Legion\Documents\phantom-ai\meta-skills\scripts\plugin-auto-update.ps1"
$trigger1 = New-ScheduledTaskTrigger -Daily -At 03:00
$trigger2 = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "MetaSkills-Plugin-Auto-Update" -Action $action -Trigger @($trigger1,$trigger2) -Description "Auto-refresh Plugin-Cache aus Source — E207 prevention" -User $env:USERNAME
#>
