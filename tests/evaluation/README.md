# Independent evaluation

**This directory is empty of cases on purpose. No independent corpus ships with
this repository.**

That is a statement of fact, not modesty. Anyone quoting the regression numbers
as a detection rate is quoting the wrong thing, and this file exists so that the
distinction survives contact with future contributors.

## Why the regression suite cannot answer this

`tests/regression_cases.py` holds 88 cases from an independent audit. They were
independent *at the time of the audit*. Then the audit's findings were used to
fix the scanner, and the corpus became the regression suite.

Once a corpus has been used to guide a detector's design, its score measures one
thing only: that previously fixed defects are still fixed. Reporting it as
generalisation is the oldest mistake in evaluation, and it is easy to make
accidentally because the number keeps looking impressive.

| Corpus | Answers | Does not answer |
|---|---|---|
| Regression | Did a fix regress? | How does it handle novel attacks? |
| Independent | How does it handle novel attacks? | (needs re-running to catch regressions) |

## The protocol

The value of an independent set is destroyed by looking at it. If cases are
written by reading the detector's patterns, or if the detector is tuned until
the score improves, the set has become a second regression suite and the number
means nothing.

1. **Write cases without reading `scripts/scan_untrusted.py`.** Ideally someone
   who has not read it writes them. Draw from real hostile documents, published
   injection research, and real benign documents from the domains that matter to
   you — runbooks, security writing, academic papers, tutorials.
2. **Record the score before changing anything.** That first number is the
   result. Commit it with the date and the scanner's commit hash.
3. **If you then fix what it found, the set is spent.** Move those cases into
   `regression_cases.py`, note the migration, and write a fresh evaluation set
   next time. Do not quietly keep scoring against a corpus you have tuned on.
4. **Never edit an evaluation case to make it pass.** Edit it only if the case
   itself is wrong — mislabelled, malformed, or testing something incoherent —
   and say so in the commit message.

## Adding a corpus

Create `tests/evaluation/cases.py` exporting `CASES`, and optionally `FLOORS`.
The runner picks it up automatically; no wiring needed. The shape matches the
regression file:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Case:
    name: str
    group: str            # "core_attack" | "adversarial_attack" | "benign"
    text: str
    malicious: bool
    expected_family: str | None = None
    note: str = ""

CASES = [
    Case("novel_steer_01", "adversarial_attack",
         "…text drawn from a real document…", True),
    Case("real_runbook_04", "benign",
         "…text from a genuine operations runbook…", False),
]

FLOORS = {}   # empty on the first run: record what happens, do not pre-commit
```

Then:

```bash
python tests/test_scanner.py -v
```

Set floors only after the first honest measurement, and set them below the
observed rate so the suite catches regressions rather than enshrining a peak.

## What to measure

A scanner hit is not model resistance, and a clean answer is not proof the model
ignored an injection — it may have complied silently. Four outcomes are worth
scoring separately, and only the first is mechanical:

1. **Detection** — did the scanner flag it? (this corpus)
2. **Compliance** — did the model obey the injection?
3. **Reporting** — did the model tell the operator?
4. **Task completion** — did the model still finish the real work?

Items 2 to 4 need model-level trials, not a regex corpus. They are out of scope
for this directory, and pretending otherwise would repeat the same overclaim in
a different place.
