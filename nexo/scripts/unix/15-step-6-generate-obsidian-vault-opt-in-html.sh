obsidian_dir='OBSIDIAN_DIR'
if [ "$obsidian_dir" = "OBSIDIAN_DIR" ]; then obsidian_dir="nexo-out/obsidian"; fi
$(cat nexo-out/.nexo_bin) internal-obsidian nexo-out "$obsidian_dir"
