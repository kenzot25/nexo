$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-manifest nexo-out"
Remove-Item -ErrorAction SilentlyContinue nexo-out\.nexo_detect.json, nexo-out\.nexo_extract.json, nexo-out\.nexo_ast.json, nexo-out\.nexo_semantic.json, nexo-out\.nexo_analysis.json, nexo-out\.nexo_labels.json
Remove-Item -ErrorAction SilentlyContinue nexo-out\.needs_update
