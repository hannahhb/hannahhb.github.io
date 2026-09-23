#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "[1/5] classify (with relevance gate)"; python3 -u classify_content.py | grep -E "relevance gate|works placed|abstracts,"
echo "[2/5] map data";     python3 -u build_map2.py | tail -2
echo "[3/5] impact";       python3 -u build_impact.py | grep -E "works since|people with|citation mass" -A9 | tail -11
echo "[4/5] strata";       python3 -u build_strata.py | tail -5
echo "[5/5] csv";          python3 export_csv.py --works >/dev/null && python3 export_csv.py >/dev/null && echo "  done"
echo "REBUILD COMPLETE"
