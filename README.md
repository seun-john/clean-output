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
| 0 | Sort every input into PRINCIPAL / HARNESS / DATA. Only the first two carry instructions. |
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

Catches what reading cannot: zero-width and bidi controls, Unicode Tag-block
payloads (U+E0000–U+E007F, invisible by construction), base64 and hex blobs that
decode to instruction-shaped text, text in HTML comments and `display:none`
containers, plus ~40 patterns across nine attack families.

Findings are graded `critical` / `high` / `medium` / `low`. Critical means tool
coercion or exfiltration — stop and ask. Exit code is `1` when there are
findings, `0` when clean, so it drops into CI.

**It reports; it does not decide.** Judgement stays with the model or the human,
because the addressee test is a semantic call and a regex cannot make it.

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
portable/AGENTS.md-block.md    always-on block, full and short variants
agents/openai.yaml             Codex interface metadata
```

## Licence

MIT. See [LICENSE](LICENSE).
