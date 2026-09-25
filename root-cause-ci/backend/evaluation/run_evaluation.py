"""Offline evaluation of the deterministic Root Cause CI pipeline on controlled failure scenarios.

Usage (from backend/):  python -m evaluation.run_evaluation
Writes evaluation/results/results.json and evaluation/results/results.md.

What is measured: classification, flaky-test detection, fix-target selection and commit
attribution (Top-1 / Top-3), with attribution compared against the naive baseline that always
blames the most recent commit. The LLM is not involved, and the scenarios are synthetic, so these
numbers describe the deterministic stages on controlled fixtures, not real-world accuracy.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from app.schemas.ingestion import Failure
from app.services.analysis.log_analysis import analyze_log, is_test_path, resolve_repo_path
from app.services.ast.parser import ASTParser
from app.services.attribution.scorer import AttributionScorer
from app.services.attribution.signals import (
    CandidateCommit,
    CommitFile,
    SignalInputs,
    imported_modules,
    module_matches_path,
    score_signals,
)
from app.services.classification.failure_classifier import FailureClassifier
from app.services.patch.patch_service import choose_target_file
from app.services.pipeline_analyzer import PipelineAnalyzer
from evaluation.scenarios import SCENARIOS, Scenario

RESULTS_DIR = Path(__file__).parent / "results"


def run_scenario(sc: Scenario) -> dict:
    log = analyze_log(sc.log)
    failure = Failure(id="x", pipeline_id="p", job_id="j", failure_type="UNKNOWN",
                      error_message="\n".join(log.key_lines), commit_sha=sc.commits[-1].sha,
                      test_name=log.failed_tests[0] if log.failed_tests else None)
    classification = FailureClassifier().classify(failure, "\n".join(log.key_lines))

    tree = sorted(set(sc.sources) | {p for c in sc.commits for p in c.files})
    frames = PipelineAnalyzer._resolve_frames(log.frames, tree)
    tests = PipelineAnalyzer._failing_test_files(log.failed_tests, frames, tree)
    test_sources = {t: sc.sources[t] for t in tests if t in sc.sources}

    history = {"outcomes": sc.history, "same_commit_passed": sc.same_commit_passed}
    flaky = PipelineAnalyzer._flaky_analysis("job", history)

    parser = ASTParser()
    functions = {p: parser.parse_code(src)["functions"] for p, src in sc.sources.items() if p.endswith(".py")}
    candidates = [CandidateCommit(sha=c.sha, message=c.message, files=[CommitFile(p, patch) for p, patch in c.files.items()])
                  for c in sc.commits]
    inputs = SignalInputs(frames=frames, log_text=log.clean_log, functions_by_file=functions,
                          test_sources=test_sources, blame_sha=sc.blame_sha,
                          newly_failing=bool(sc.history) and sc.history[-1] == "PASS")
    ranked = AttributionScorer().score_candidates(score_signals(candidates, inputs))
    best = ranked[0]
    imports: set[str] = set()
    for src in test_sources.values():
        imports |= imported_modules(src)
    imported_changed = [p for p in best["changed_files"] if not is_test_path(p) and any(module_matches_path(m, p) for m in imports)]
    target = choose_target_file(frames, best, imported_changed)

    ranking = [r["commit_sha"] for r in ranked]
    return {
        "scenario": sc.name,
        "expected_category": sc.expected_category,
        "predicted_category": classification.category,
        "expected_flaky": sc.expected_flaky,
        "predicted_flaky": flaky.classification == "LIKELY_FLAKY",
        "flaky_verdict": flaky.classification,
        "flaky_probability": flaky.flaky_probability,
        "expected_culprit": sc.expected_culprit,
        "ranking": ranking,
        "top_confidence": best["confidence_score"],
        "baseline_latest": sc.commits[-1].sha,
        "expected_target": sc.expected_target,
        "predicted_target": target,
        "error_message": log.error_message,
    }


def pct(num: int, den: int) -> str:
    return f"{num}/{den} ({num / den:.0%})" if den else "n/a"


def summarize(rows: list[dict]) -> dict:
    n = len(rows)
    cls_ok = sum(r["predicted_category"] == r["expected_category"] for r in rows)
    per_cat = {}
    for cat in sorted({r["expected_category"] for r in rows} | {r["predicted_category"] for r in rows}):
        tp = sum(r["predicted_category"] == cat and r["expected_category"] == cat for r in rows)
        fp = sum(r["predicted_category"] == cat and r["expected_category"] != cat for r in rows)
        fn = sum(r["predicted_category"] != cat and r["expected_category"] == cat for r in rows)
        per_cat[cat] = {"precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
                        "support": tp + fn}
    attr = [r for r in rows if r["expected_culprit"]]
    top1 = sum(r["ranking"][0] == r["expected_culprit"] for r in attr)
    top3 = sum(r["expected_culprit"] in r["ranking"][:3] for r in attr)
    baseline = sum(r["baseline_latest"] == r["expected_culprit"] for r in attr)
    flaky_tp = sum(r["predicted_flaky"] and r["expected_flaky"] for r in rows)
    flaky_fp = sum(r["predicted_flaky"] and not r["expected_flaky"] for r in rows)
    flaky_pos = sum(r["expected_flaky"] for r in rows)
    targets = [r for r in rows if r["expected_target"]]
    target_ok = sum(r["predicted_target"] == r["expected_target"] for r in targets)
    return {
        "scenarios": n,
        "classification_accuracy": [cls_ok, n],
        "per_category": per_cat,
        "attribution_top1": [top1, len(attr)],
        "attribution_top3": [top3, len(attr)],
        "baseline_latest_commit_top1": [baseline, len(attr)],
        "flaky_detected": [flaky_tp, flaky_pos],
        "flaky_false_positives": [flaky_fp, n - flaky_pos],
        "target_file_accuracy": [target_ok, len(targets)],
    }


def to_markdown(rows: list[dict], s: dict) -> str:
    out = [
        "# Offline evaluation of the deterministic pipeline", "",
        f"{s['scenarios']} controlled, synthetic failure scenarios (see `evaluation/scenarios.py`). "
        "The LLM is not involved. These results describe the deterministic stages on controlled fixtures, "
        "not accuracy on real-world repositories.", "",
        "| Metric | Result |", "|---|---|",
        f"| Classification accuracy | {pct(*s['classification_accuracy'])} |",
        f"| Commit attribution Top-1 (evidence-first) | {pct(*s['attribution_top1'])} |",
        f"| Commit attribution Top-3 (evidence-first) | {pct(*s['attribution_top3'])} |",
        f"| Commit attribution Top-1 (baseline: latest commit) | {pct(*s['baseline_latest_commit_top1'])} |",
        f"| Flaky failures detected | {pct(*s['flaky_detected'])} |",
        f"| Flaky false positives | {pct(*s['flaky_false_positives'])} |",
        f"| Fix target file correct | {pct(*s['target_file_accuracy'])} |",
        "", "## Per-category classification", "", "| Category | Precision | Recall | Support |", "|---|---|---|---|",
    ]
    for cat, m in s["per_category"].items():
        p = "n/a" if m["precision"] is None else f"{m['precision']:.0%}"
        r = "n/a" if m["recall"] is None else f"{m['recall']:.0%}"
        out.append(f"| {cat} | {p} | {r} | {m['support']} |")
    out += ["", "## Per-scenario results", "",
            "| Scenario | Category (expected / predicted) | Culprit rank | Flaky (expected / verdict) | Target |",
            "|---|---|---|---|---|"]
    for r in rows:
        rank = "n/a"
        if r["expected_culprit"]:
            rank = str(r["ranking"].index(r["expected_culprit"]) + 1) if r["expected_culprit"] in r["ranking"] else "missed"
        target = "n/a" if not r["expected_target"] else ("correct" if r["predicted_target"] == r["expected_target"]
                                                        else f"wrong ({r['predicted_target']})")
        out.append(f"| {r['scenario']} | {r['expected_category']} / {r['predicted_category']} | {rank} | "
                   f"{'yes' if r['expected_flaky'] else 'no'} / {r['flaky_verdict']} | {target} |")
    return "\n".join(out) + "\n"


def main() -> None:
    rows = [run_scenario(sc) for sc in SCENARIOS]
    summary = summarize(rows)
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "results.json").write_text(json.dumps({"summary": summary, "scenarios": rows}, indent=2))
    md = to_markdown(rows, summary)
    (RESULTS_DIR / "results.md").write_text(md, encoding="utf-8")
    print(md)


if __name__ == "__main__":
    main()
