#!/bin/bash
# When the pdebug groups are done, submit the full 300-task run to pbatch.
#
# Separate from `overnight.sh` rather than appended to it: that script was
# already running when this was written, and editing a live bash script is how
# you get it to resume at the wrong byte.
set -uo pipefail
P=/usr/WS2/haridev/phronix
source "$P/scripts/bench-root.sh"
PBENCH=$(bench_root)

# Wait for the groups driver to finish, however it ends.
while pgrep -f "overnight.sh" >/dev/null 2>&1 || pgrep -f "start-overnight.sh" >/dev/null 2>&1; do
    sleep 120
done
"$P/scripts/kill.sh" >/dev/null 2>&1

# 32 nodes is 128 replicas; 60 tasks is 120 arms, so about one arm per replica.
# That ratio is the one that matters — measured on the small fleet, four
# requests sharing a replica cut each agent to a quarter of its decode rate and
# attempts stopped finishing inside their budget.
out=$("$P/scripts/bench-batch.sh" --submit -N 32 -t 24h -q pbatch \
        --size 300 --index 1 --parallel 60 --name lite300 2>&1)
{
  echo ""
  echo "## The full 300-task run"
  echo ""
  echo '```'
  echo "$out"
  echo '```'
  echo ""
  echo "Submitted after the pdebug groups. 32 nodes, 24h, all 300 tasks in one"
  echo "session, 60 at a time. Watch it with \`scripts/top.sh --once\`; the"
  echo "batch job's own log is named in the block above."
} >> "$P/interesting.md"
echo "$out"
