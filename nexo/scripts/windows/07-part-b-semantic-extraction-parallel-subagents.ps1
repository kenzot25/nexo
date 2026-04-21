$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-cache-check nexo-out\.nexo_detect.json nexo-out\.nexo_cached.json nexo-out\.nexo_uncached.txt"
