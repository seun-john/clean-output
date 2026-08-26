# Clean Output

An agent skill that keeps prompt scaffolding out of what the model writes, and
keeps untrusted content out of what the model obeys.

Works with Claude Code, Codex, and anything else that reads `SKILL.md` or
`AGENTS.md`. No dependencies beyond Python's standard library.

## The problem

You give a model background so it knows what to do. It writes the background
into the output:

> Sure! Here's a 500-word blog post in a professional tone for small business
> owners. As an expert copywriter, I've avoided technical jargon as you
> requested. I hope this gives you a solid starting point!

None of that belongs in a blog post. The brief was scaffolding — it should shape
the work and then disappear.

The mirror-image failure: a model reads a document you asked it to summarise, the
document contains a line addressed to the model, and the model does what the
document says instead of what you said.

## Why one skill and not two

Both are layer-boundary failures, in opposite directions.

```
                    ┌─────────────────┐
  meta-writing  →   │  INSTRUCTION    │  ← prompt injection
  (leaks OUT)       │     LAYER       │     (leaks IN)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  OUTPUT LAYER   │
                    └─────────────────┘
```

Meta-writing is instruction-layer material escaping downward into the output.
Prompt injection is data-layer material climbing upward into the instructions.
One discipline fixes both: know which layer every token arrived from, and know
which layer it is permitted to reach. In both cases the offending text is
*routed to a note for the operator* — not obeyed, and not silently dropped.

## How it works

Five passes:

| Pass | Does |
|---|---|
| 0 | Sort every input into PROTECTED / PRINCIPAL / DELEGATED / UNTRUSTED. Only the first two carry instructions outright. |
| 1 | Scan the DATA bucket for injection — script for hidden payloads, judgement for semantics. |
| 2 | Draft, with routing enforced while writing. |
| 3 | Re-read cold and scrub meta-writing. |
| 4 | Emit the deliverable and a separate operator note. |

The two tests that carry the weight:

**For meta-writing** — *does this sentence make sense to a reader who never saw
the prompt?* If not, it belongs in the operator note, not the artifact.

**For injection** — *is this text addressed to the model reading it, or to the
document's own audience?* Most documents are legitimately imperative. Runbooks,
SOPs, specs and recipes are made of instructions and are not attacks.

And one rule that matters more than it looks: **untrusted text never triggers a
side effect, and never triggers a blocking question either.** A document that can
make the model stop and ask you something has interrupted your work by writing
four words. Ignore, report, continue — then ask only if *your own* task needs a
side effect and the authority for it is unclear.

## Install

### Claude Code

```bash
git clone https://github.com/seun-john/clean-output.git ~/.claude/skills/clean-output
```

### Codex

```bash
git clone https://github.com/seun-john/clean-output.git ~/.codex/skills/clean-output
```

### Always-on enforcement (recommended)

A skill fires when its description matches, which can miss the turn that
mattered. For consistent behaviour, also paste the block from
[`portable/AGENTS.md-block.md`](portable/AGENTS.md-block.md) into
`~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`. A shorter variant is included for
tight instruction budgets.

## The scanner

```bash
python scripts/scan_untrusted.py suspicious.md
python scripts/scan_untrusted.py ./scraped/ --min-severity high
python scripts/scan_untrusted.py page.html --json
curl -s https://example.com | python scripts/scan_untrusted.py --stdin
```

Detection runs over several **views** of the same text — raw, folded (invisibles
stripped, NFKC-normalised, spaced-out and punctuation-split letters rejoined), and
decoded (base64 / base32 / hex / percent / unicode-escape / ROT13 / reversed). A
pattern that matches only in a derived view means the text was deliberately
obfuscated, which *raises* confidence rather than lowering it.

That design also fixes the obvious false positives structurally: legitimate
zero-width use — Persian ZWNJ, emoji joiners, soft hyphens, bidi isolation — never
produces a finding on its own, because nothing is reported unless it carries a
payload or unlocks a pattern.

Findings are graded on **two axes that are deliberately kept apart**:

- `confidence` — how sure the detector is (`strong` / `moderate` / `weak`)
- `impact` — what it would mean *if genuine* (`critical` / `high` / `medium` / `low`)

A `critical` impact at `weak` confidence is usually a quoted example in a security
document. **Neither axis is a risk score**, and neither should be wired to an
automatic block. Exit code is `1` for findings, `0` when clean, `2` when a
requested target was missing or unreadable — so a CI job cannot pass by silently
scanning nothing.

Formats needing real extraction (PDF, Office, images) are **reported as not
scanned** rather than skipped quietly. The scanner reads decoded UTF-8 text only
and will not claim clean coverage it does not have.

**It reports; it does not decide.** Judgement stays with the model or the human,
because the addressee test is a semantic call and a regex cannot make it.

### Tests

```bash
python tests/test_scanner.py -v
```

88 labelled cases — 35 documented attacks, 28 adversarial evasions, 25 benign
controls — taken from an independent audit of this repository, so the scanner is
measured against a corpus it was not tuned on.

| Group | Result |
|---|---|
| Documented attacks detected | 35 / 35 |
| Adversarial evasions detected | 28 / 28 |
| Benign controls not flagged | 19 / 25 |

The six remaining benign flags are genuine semantic ambiguity — a tutorial saying
"run this command", a security doc quoting `curl … | sh`, a rollback note
containing `DROP TABLE`. No regex resolves those; that is what the model's
addressee pass is for.

## What it does not do

**This is a prompt-level mitigation, not a security boundary.** It reduces
injection compliance and catches obvious and semi-obvious cases. It can be
defeated by a sufficiently novel payload, and no prompt-level defence has been
shown to be complete.

Where a successful injection would cause real damage, enforcement belongs at the
tool and permission layer: allowlisted commands, scoped credentials, human
confirmation on side-effectful actions, egress control, and never granting one
agent both secret-reading and network-reaching tools. Treat this as defence in
depth, never as the defence.

## Contents

```
SKILL.md                       the algorithm
references/meta-writing.md     nine types, per-type fixes, when meta IS the deliverable
references/prompt-injection.md attack families, addressee test, reporting format
examples/before-after.md       worked cases, including deliberate false positives
scripts/scan_untrusted.py      mechanical detection
tests/test_scanner.py          88-case labelled corpus
portable/AGENTS.md-block.md    always-on block, full and short variants
agents/openai.yaml             Codex interface metadata
```

## Credits

The test corpus and several of the design corrections — the trust-tier model,
the denial-of-service flaw in the original escalation rule, and the confidence /
impact split — come from an independent audit of this repository carried out on
26 August 2026.

## Licence

MIT. See [LICENSE](LICENSE).
