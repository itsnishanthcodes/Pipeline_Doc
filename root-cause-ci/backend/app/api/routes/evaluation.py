import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/evaluation", tags=["evaluation"])

RESULTS_PATH = Path(__file__).resolve().parents[3] / "evaluation" / "results" / "results.json"


@router.get("/summary")
def evaluation_summary():
    """Latest offline evaluation of the deterministic pipeline (run `python -m evaluation.run_evaluation`)."""
    if not RESULTS_PATH.exists():
        raise HTTPException(status_code=404, detail="No evaluation results yet. Run python -m evaluation.run_evaluation.")
    data = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    return {
        "summary": data.get("summary", {}),
        "scenarios": [
            {k: s.get(k) for k in ("scenario", "expected_category", "predicted_category", "expected_flaky",
                                   "flaky_verdict", "expected_culprit", "ranking", "baseline_latest")}
            for s in data.get("scenarios", [])
        ],
        "note": "Controlled, synthetic failure scenarios. The LLM is not involved; this is not real-world accuracy.",
    }
