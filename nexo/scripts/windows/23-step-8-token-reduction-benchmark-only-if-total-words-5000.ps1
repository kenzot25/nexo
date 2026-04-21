$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN benchmark nexo-out/graph.json"
