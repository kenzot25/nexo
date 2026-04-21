$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
Invoke-Expression "& $BIN internal-transcribe nexo-out\.nexo_detect.json nexo-out\.nexo_transcripts.json"
