if (-not (Test-Path "nexo-out\.nexo_bin")) {
    $nexoCmd = Get-Command nexo -ErrorAction SilentlyContinue
    if ($nexoCmd -and (Invoke-Expression "& $($nexoCmd.Source) stats --out-dir .") -eq 0) {
        mkdir -p nexo-out
        $nexoCmd.Source | Out-File -FilePath "nexo-out\.nexo_bin" -Encoding utf8
    } else {
        $python = "python"
        mkdir -p nexo-out
        "$python -m nexo" | Out-File -FilePath "nexo-out\.nexo_bin" -Encoding utf8
    }
}
