# claude-tabs scan — Security-Scan aller Sessions auf Klartext-Credentials
# Usage: . .\scan.ps1 [-MaxFiles 50]
#
# Sucht Regex-Patterns für Klartext-Tokens / Secrets über alle Session-JSONLs.
# Findet das was heute passiert ist (GitHub PAT geleaked in der Documents-Session).

param(
    [int]$MaxFiles = 50
)

$base = "$env:USERPROFILE\.claude\projects"

# Token-Patterns (extend as needed)
$patterns = @{
    'GitHub PAT'      = 'ghp_[A-Za-z0-9]{36,}'
    'GitHub OAuth'    = 'gho_[A-Za-z0-9]{36,}'
    'GitHub Fine-Grained' = 'github_pat_[A-Za-z0-9_]{82,}'
    'OpenAI Key'      = 'sk-(proj-)?[A-Za-z0-9]{40,}'
    'Anthropic Key'   = 'sk-ant-[A-Za-z0-9_-]{90,}'
    'AWS Access Key'  = 'AKIA[0-9A-Z]{16}'
    'JWT-like Token'  = 'eyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}'
    'Slack Bot Token' = 'xox[bp]-[A-Za-z0-9-]{40,}'
    'Stripe Key'      = '(sk|pk)_(test|live)_[A-Za-z0-9]{24,}'
}

$findings = @()

$files = Get-ChildItem -Path $base -Directory | ForEach-Object {
    Get-ChildItem -Path $_.FullName -Filter "*.jsonl" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
} | Sort-Object LastWriteTime -Descending | Select-Object -First $MaxFiles

foreach ($file in $files) {
    $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }

    foreach ($name in $patterns.Keys) {
        $pattern = $patterns[$name]
        $matches = [regex]::Matches($content, $pattern)
        foreach ($m in $matches) {
            $findings += [PSCustomObject]@{
                File        = $file.Name
                ProjectDir  = $file.Directory.Name
                TokenType   = $name
                Preview     = $m.Value.Substring(0, [math]::Min(15, $m.Value.Length)) + '...'
                FullMatch   = $m.Value  # Bewusst voll für Joe zur Identifikation
            }
        }
    }
}

if ($findings.Count -eq 0) {
    Write-Host "✅ Keine Klartext-Credentials in den letzten $MaxFiles Sessions gefunden."
} else {
    Write-Host "🔴 $($findings.Count) potenzielle Token-Leaks gefunden:"
    Write-Host ""
    $findings | Select-Object ProjectDir, TokenType, Preview | Format-Table -AutoSize
    Write-Host ""
    Write-Host "Volle Token-Strings in `$findings.FullMatch verfügbar (zum Identifizieren welcher Token rotiert werden muss)."
}

return $findings
