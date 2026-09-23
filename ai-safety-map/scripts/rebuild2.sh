#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "[1/5] map data";  python3 -u build_map2.py | tail -3
echo "[2/5] impact";    python3 -u build_impact.py | grep -E "works since|people with|citation mass" -A9 | tail -11
echo "[3/5] terrain";   python3 -u build_terrain.py | tail -9
echo "[4/5] wave";      python3 -u build_wave.py | tail -2
echo "[5/5] csv";       python3 export_csv.py --works >/dev/null && python3 export_csv.py >/dev/null && echo "  done"
echo "REBUILD COMPLETE"
