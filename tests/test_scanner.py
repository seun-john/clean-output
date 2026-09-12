#!/usr/bin/env python3
"""Runner for the scanner's labelled corpora.

Two corpora, kept apart on purpose:

  regression   tests/regression_cases.py -- 88 cases from an independent audit.
               The scanner was fixed in response to that audit, so these results
               show that known defects stay fixed. They are NOT out-of-sample
               performance and must never be quoted as a detection rate.

  evaluation   tests/evaluation/cases.py -- optional, absent by default.
               Genuinely unseen cases, written without reference to the
               detector's patterns and scored once before any tuning.
               See tests/evaluation/README.md for the protocol.

Run:  python tests/test_scanner.py            # summary
      python tests/test_scanner.py -v         # per-case failures
      python tests/test_scanner.py --json     # machine-readable

Exit 0 if every group in every present corpus meets its floor, 1 otherwise.
A missing evaluation corpus is reported, not treated as a failure.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANNER = ROOT / "scripts" / "scan_untrusted.py"
TESTS = Path(__file__).resolve().parent


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


scan = _load(SCANNER, "clean_output_scanner")
regression = _load(TESTS / "regression_cases.py", "regression_cases")


def evaluate(case) -> dict:
    findings = scan.scan_text(case.text, case.name)
    families = sorted({f.family for f in findings})
    confidences = {f.confidence for f in findings}
    detected = bool(findings)
    # A benign case that only yields weak/moderate findings is the detector
    # behaving as designed: report the signal, lower the certainty. Tracked
    # separately from "silent", which is the stricter bar.
    detected_confident = scan.STRONG in confidences
    family_hit = case.expected_family is None or case.expected_family in families
    return {
        "name": case.name,
        "group": case.group,
        "malicious": case.malicious,
        "detected": detected,
        "detected_confident": detected_confident,
        "families": families,
        "confidences": sorted(confidences),
        "expected_family": case.expected_family,
        "passed": (detected == case.malicious) and (not case.malicious or family_hit),
    }


def run_corpus(cases, floors: dict, label: str, verbose: bool) -> tuple[bool, dict]:
    results = [evaluate(c) for c in cases]
    groups: dict[str, list[dict]] = {}
    for r in results:
        groups.setdefault(r["group"], []).append(r)

    print(f"{label}: {len(results)} cases")
    ok = True
    summary: dict[str, dict] = {}

    for group, rows in sorted(groups.items()):
        if group == "benign":
            good = [r for r in rows if not r["detected"]]
            quiet = [r for r in rows if not r["detected_confident"]]
            metric = "silent"
        else:
            good = [r for r in rows if r["passed"]]
            quiet = good
            metric = "detected"

        rate = len(good) / len(rows)
        floor = floors.get(group, 0.0)
        status = "PASS" if rate >= floor else "FAIL"
        if rate < floor:
            ok = False

        line = (f"  {status}  {group:20} {len(good):>2}/{len(rows):<2} {metric}"
                f"  {rate:6.1%}  (floor {floor:.0%})")
        if group == "benign":
            line += f"   [{len(quiet)}/{len(rows)} not flagged at strong]"
        print(line)

        summary[group] = {
            "total": len(rows), "good": len(good),
            "rate": round(rate, 4), "floor": floor, "status": status,
        }
        if group == "benign":
            summary[group]["not_strong"] = len(quiet)

        if verbose:
            for r in rows:
                bad = r["detected"] if group == "benign" else not r["passed"]
                if not bad:
                    continue
                if group == "benign":
                    why = f"flagged at {'/'.join(r['confidences'])}"
                elif not r["detected"]:
                    why = "missed"
                else:
                    why = (f"wrong family: got {r['families']}, "
                           f"want {r['expected_family']}")
                print(f"           - {r['name']}: {why}")
    return ok, summary


def load_evaluation():
    """The independent corpus, if one has been added."""
    path = TESTS / "evaluation" / "cases.py"
    if not path.exists():
        return None
    module = _load(path, "evaluation_cases")
    return module


def main() -> int:
    verbose = "-v" in sys.argv
    as_json = "--json" in sys.argv

    ok, regression_summary = run_corpus(
        regression.CASES, regression.FLOORS, "regression", verbose)
    print("  note: the scanner was fixed using these cases -- regression "
          "coverage, not\n        out-of-sample performance.")
    print()

    evaluation_summary = None
    ev = load_evaluation()
    if ev is None:
        print("evaluation: no independent corpus present.")
        print("  This repository ships no unseen evaluation set. Regression")
        print("  numbers above must not be quoted as a detection rate.")
        print("  To add one, see tests/evaluation/README.md.")
    else:
        ev_ok, evaluation_summary = run_corpus(
            ev.CASES, getattr(ev, "FLOORS", {}), "evaluation", verbose)
        ok = ok and ev_ok
    print()

    if as_json:
        print(json.dumps({
            "regression": regression_summary,
            "evaluation": evaluation_summary,
            "evaluation_present": ev is not None,
            "pass": ok,
        }, indent=2))
    else:
        print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
