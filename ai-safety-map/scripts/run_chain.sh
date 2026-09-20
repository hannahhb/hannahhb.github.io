#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "[1/4] build_dataset";   python3 -u build_dataset.py --clusters 16 | grep -E "people with"
echo "[2/4] assign_taxonomy"; python3 -u assign_taxonomy.py | grep -E "taxonomy:|works:"
echo "[3/4] export CSVs";     python3 export_csv.py --works >/dev/null && python3 export_csv.py >/dev/null && echo "  done"
echo "[4/4] build_map_data";  python3 -u build_map_data.py
echo "CHAIN COMPLETE"
