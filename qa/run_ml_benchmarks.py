from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ml.benchmark_hub import build_ml_overview


def main() -> int:
    report = build_ml_overview()
    report_path = Path(report["paths"]["reports"]) / "ml_overview.json"
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))
    print(f"[ML] Rapport ecrit dans {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
