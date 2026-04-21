$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
$RESULT = Invoke-Expression "& $BIN internal-detect-incremental . nexo-out"
Set-Content -Path nexo-out\.nexo_incremental.json -Value $RESULT
