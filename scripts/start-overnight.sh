#!/bin/bash
# Wait for group 1 (already running on its own allocation), record it, then
# hand over to the driver for groups 2..10.
set -uo pipefail
P=/usr/WS2/haridev/phronix
OUT=/p/lustre5/haridev/phronix-bench/runs/claude-0827-000348
ALLOC=f3UgwcNsaE15

while pgrep -f "benchmark.cli run" >/dev/null 2>&1; do
    state=$(flux jobs -a --no-header 2>/dev/null | awk -v j="$ALLOC" '$1==j{print $5}')
    [ "$state" = "R" ] || break
    sleep 60
done
"$P/scripts/kill.sh" >/dev/null 2>&1
flux cancel "$ALLOC" 2>/dev/null

{
  summary=$(cd "$P" && scripts/top.sh "$OUT" --once 2>/dev/null | sed -n 2p | sed 's/^ *//' | cut -c1-150)
  skills=$(ls "$OUT"/claude-phronix/store/.phronix/capabilities/tasks/ 2>/dev/null | wc -l)
  used=$(grep -rh "skill-use" "$OUT"/*/tasks/*/trace.log 2>/dev/null | grep -c "loaded \`")
  echo ""
  echo "### group 1 — \`$(basename "$OUT")\`"
  echo ""
  echo '```'
  echo "$summary"
  echo '```'
  echo ""
  echo "- run: \`$OUT\`"
  echo "- skills written: **$skills**   attempts that loaded one: **$used**"
  echo "- \`scripts/top.sh $OUT --once\`"
} >> "$P/interesting.md"

exec "$P/scripts/overnight.sh" 2 10
