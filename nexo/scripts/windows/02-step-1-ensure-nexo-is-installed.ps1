# Resolve the 'nexo' command (binary or python)
$nexoCmd = Get-Command nexo -ErrorAction SilentlyContinue

if ($nexoCmd) {
    # Verify it works
    & $nexoCmd.Source stats --out-dir . 2>$null >$null
    if ($LASTEXITCODE -eq 0) {
        $nexoCmd.Source | Out-File -FilePath "nexo-out\.nexo_bin" -Encoding utf8
        exit 0
    }
}

# Fallback to Python
$python = "python"
& $python -c "import nexo" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install nexo -q 2>$null
    if ($LASTEXITCODE -ne 0) {
        & $python -m pip install nexo -q --break-system-packages 2>&1 | Select-Object -Last 3
    }
}

& $python -c "import nexo" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "nexo is unavailable."
    exit 1
}

# Save the python execution command
"$python -m nexo" | Out-File -FilePath "nexo-out\.nexo_bin" -Encoding utf8
