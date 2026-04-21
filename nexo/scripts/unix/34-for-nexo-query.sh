DFS_FLAG=""
if [ "MODE" = "dfs" ]; then DFS_FLAG="--dfs"; fi
$(cat nexo-out/.nexo_bin) query "QUESTION" $DFS_FLAG --budget BUDGET --graph nexo-out/graph.json
