$BIN = (Get-Content nexo-out\.nexo_bin -Raw).Trim()
$obsidian_dir = 'OBSIDIAN_DIR'
if ($obsidian_dir -eq 'OBSIDIAN_DIR') { $obsidian_dir = 'nexo-out/obsidian' }
Invoke-Expression "& $BIN internal-obsidian nexo-out '$obsidian_dir'"
