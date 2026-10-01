# Clean Output

An agent skill that keeps prompt scaffolding out of what the model writes, and
keeps untrusted content out of what the model obeys.

Works with Claude Code, Codex, and anything else that reads `SKILL.md` or
`AGENTS.md`. The skill and its scanner use the Python standard library only.
Document extraction is a separate optional script; it also works with the
standard library, and will use a PDF library if you happen to have one.

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

**Two modes, and most work needs only the first.** Running a provenance audit
before writing a cover letter is theatre, and a skill that feels like bureaucracy
gets switched off before the day it matters.

**Clean-output mode** — the default. Ordinary writing and editing from material
you supplied. Write the deliverable, keep the scaffolding out, scrub, and add an
operator note only if there is something worth saying. Passes 2–4.

**Boundary-protection mode** — when the work touches material someone else wrote:
fetched pages, scraped text, third-party documents, an unfamiliar repository,
external tool output. All five passes.

The switch is one question: *could any part of this text have been written by
someone who wants to influence me?*

| Pass | Does | Mode |
|---|---|---|
| 0 | Sort inputs into PROTECTED / PRINCIPAL / DELEGATED / UNTRUSTED | boundary only |
| 1 | Extract, scan, and review untrusted material | boundary only |
| 2 | Draft, with routing enforced while writing | both |
| 3 | Re-read cold and scrub meta-writing | both |
| 4 | Emit the deliverable, and a note only if it carries weight | both |

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
python scripts/scan_untrusted.py ./scraped/ --min-confidence strong
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
automatic block.

Context lowers confidence without suppressing the finding. A match inside a code
fence, a blockquote, or a quotation is marked `quoted/code`; a match near
documentation markers ("for example", "anti-pattern", "according to") is marked
`documentary context`; a `run this command` with no command anywhere near it is
marked accordingly. Each drops the finding a step. None of them hide it.

Exit codes: `0` clean **and** fully covered, `1` findings, `2` incomplete
coverage — a target was missing, unreadable, or in a format the scanner cannot
decode. **A run that could not read everything it was pointed at never exits 0**,
so a CI gate cannot pass by scanning nothing. The JSON carries the same fact as
`coverage_complete`.

Symlinks are not followed by default; a linked directory can loop, or point
outside the tree you named. `--follow-symlinks` opts in, with loop detection.

## Extraction: PDF and Office documents

The scanner reads decoded UTF-8 text and nothing else. `extract_untrusted.py` is
the front end that turns documents into that text, kept in a separate file so the
scanner keeps its zero-dependency guarantee.

```bash
python scripts/extract_untrusted.py report.docx            # text to stdout
python scripts/extract_untrusted.py ./inbox/ --scan        # extract, then scan
python scripts/extract_untrusted.py deck.pptx --json       # structured output

python scripts/extract_untrusted.py paper.pdf | \
    python scripts/scan_untrusted.py --stdin               # explicit pipeline
```

```text
source document → extract_untrusted.py → scan_untrusted.py → addressee review
```

| Format | Method | Dependency |
|---|---|---|
| DOCX, PPTX, XLSX, ODT, EPUB | `zipfile` + `ElementTree` | none |
| IPYNB | `json` — cells *and* stored outputs | none |
| PDF | FlateDecode via `zlib`, text operators | none, best-effort |
| PDF (better) | pdfminer.six or pypdf | optional, used if installed |
| DOC, PPT, XLS, RTF, images, audio | none — reported as failures | — |

Office formats get the attention because they are ZIP archives of XML, and text
hides in parts a reader never opens: speaker notes, tracked changes, comments,
headers and footers. Each part is extracted and labelled, so a payload in slide
notes reaches the scanner with its location attached. Runs marked hidden
(`w:vanish`), coloured white, or set in sub-2.5pt type are flagged separately —
that is the classic document-borne trick and it is invisible on screen.

Stdlib PDF extraction is approximate: no font or CMap decoding, no OCR, no text
rendered as vector outlines or images. It says so on every run. Encrypted PDFs
fail loudly rather than returning empty text that would read as clean.

Anything that cannot be extracted exits `2`. **A document that could not be read
must never look like a document that was read and found clean** — that is the
single property this whole layer exists to preserve.

**It reports; it does not decide.** Judgement stays with the model or the human,
because the addressee test is a semantic call and a regex cannot make it.

### Tests

```bash
python tests/test_scanner.py -v
```

88 labelled cases — 35 documented attacks, 28 adversarial evasions, 25 benign
controls.

**Read these numbers as regression coverage, not as a detection rate.** The
corpus originated from an independent audit of this repository. That audit found
real defects, the scanner was then changed in response to them, and the same
corpus became the regression suite. Because the detector was improved with
knowledge of these cases, the results below show that fixed defects stay fixed.
They say nothing about performance on an attack nobody has thought of yet.

| Group | Result | Measures |
|---|---|---|
| Documented attacks detected | 35 / 35 | known families still caught |
| Adversarial evasions detected | 28 / 28 | known evasions still caught |
| Benign controls silent | 19 / 25 | no finding at all |
| Benign controls below strong confidence | 25 / 25 | nothing benign asserted confidently |

The six benign cases that still produce a finding are genuine semantic ambiguity
— a tutorial saying "run this command", a security document quoting `curl … | sh`,
a rollback note containing `DROP TABLE`. All six are reported at `moderate` or
`weak` confidence rather than suppressed, which is the intended behaviour:
preserve the signal, lower the certainty, leave the call to the addressee test.
No regex resolves those.

**No independent evaluation set ships with this repository.** `tests/evaluation/`
holds the protocol and the format for adding one, and deliberately no results.
Anyone reporting a real-world detection rate for this scanner would be making it
up.

## MCP server

The skill is instructions and the scanner is a script. In a client that cannot
run a script for you, `mcp/server.py` makes the mechanical half callable instead.

```bash
claude mcp add clean-output -- python /path/to/clean-output/mcp/server.py
python mcp/server.py --selftest          # 19 checks, no client needed
```

Four tools: `scan_text`, `scan_path`, `extract_document`, `extract_and_scan`.
Standard library only — MCP over stdio is newline-delimited JSON-RPC, so there is
no SDK to install. Every result quotes the suspicious text wrapped in an explicit
*data, not instructions* reminder, and carries `coverage_complete` so a document
that failed to parse never reads as clean.

Config for Claude Code, Claude Desktop, Codex, and notes on ChatGPT's HTTP-only
support: [`mcp/README.md`](mcp/README.md).

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
SKILL.md                        the two modes and the five passes
references/meta-writing.md      nine types, per-type fixes, academic exceptions,
                                when meta IS the deliverable
references/prompt-injection.md  attack families, addressee test, delegated scope,
                                reporting format
examples/before-after.md        12 worked cases, including deliberate false positives
scripts/scan_untrusted.py       mechanical detection (standard library only)
scripts/extract_untrusted.py    PDF/Office/notebook text extraction
tests/test_scanner.py           runner for both corpora
tests/regression_cases.py       the 88-case regression corpus
tests/evaluation/README.md      protocol for genuinely independent evaluation
mcp/server.py                   MCP server (standard library only)
portable/AGENTS.md-block.md     always-on block, full and short variants
agents/openai.yaml              Codex interface metadata
```

## Credits

An independent audit of this repository on 26 August 2026 found several real
defects and shaped much of the current design: the trust-tier model, the
denial-of-service flaw in the original escalation rule, the confidence/impact
split, and the 88-case corpus now used for regression testing.

Because the scanner was then improved in response to that audit, its results on
that corpus are regression coverage and not independent validation. The
distinction is spelled out in `tests/evaluation/README.md`, which also explains
how to add a genuinely unseen evaluation set.

## Licence

MIT. See [LICENSE](LICENSE).
