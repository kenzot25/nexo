New-Item -ItemType Directory -Force -Path nexo-out | Out-Null
$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-analyze nexo-out\.nexo_extract.json nexo-out\.nexo_detect.json nexo-out 'INPUT_PATH'"
