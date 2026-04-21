CODE_ONLY=$(python3 -c "import sys, json, pathlib; 
result = json.load(open('nexo-out/.nexo_incremental.json'));
new_files = result.get('new_files', {});
all_changed = [f for files in new_files.values() for f in files];
code_exts = {'.py','.ts','.js','.go','.rs','.java','.cpp','.c','.rb','.swift','.kt','.cs','.scala','.php','.cc','.cxx','.hpp','.h','.kts','.lua','.toc'};
print('true' if all(pathlib.Path(f).suffix.lower() in code_exts for f in all_changed) else 'false')" 2>/dev/null || echo "false")
echo "code_only: $CODE_ONLY"
