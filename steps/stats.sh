#!/bin/bash
# Bootstrap 95% confidence intervals by region and month.

set -euo pipefail

WORKERS=${WORKERS:-4}
OUT=${OUT:-$HOME/data/out}
export OUT

if ! [[ "$WORKERS" =~ ^[1-9][0-9]*$ ]]; then
    echo "WORKERS must be a positive integer" >&2
    exit 2
fi

pids=()

cleanup() {
    trap - EXIT
    for pid in "${pids[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    for pid in "${pids[@]}"; do
        wait "$pid" 2>/dev/null || true
    done
}

trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

python3 steps/stats_prepare.py

mkdir -p "$OUT/stats"
rm -f "$OUT"/stats/part_*.csv

for ((k=0; k<WORKERS; k++)); do
    python3 steps/stats_worker.py "$k" "$WORKERS" &
    pids+=("$!")
done

for pid in "${pids[@]}"; do
    wait "$pid"
done

trap - EXIT INT TERM

cat "$OUT"/stats/part_*.csv | sort > "$OUT/stats.csv"

echo "stats: done with $WORKERS workers"
