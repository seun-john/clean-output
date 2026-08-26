# Meta-writing: taxonomy, fixes, and limits

Meta-writing is instruction-layer material that escaped into the output layer.
You supplied background so the model would know what to do. The model wrote
*about* knowing what to do.

The fix is never a banned-phrase list. It is routing.

## The two channels

**Channel A — the deliverable.** The thing that gets copied, pasted, published,
committed, printed, or sent. Its reader never saw the prompt and never will.

**Channel B — the operator note.** A short message to the person driving the
model. Assumptions, findings, things cut, warnings.

Meta-writing is Channel B content sitting in Channel A. Deleting it is one
option. Moving it is usually the better one — the information was often worth
having, just not there.

## The test

> Does this sentence make sense to a reader who never saw the prompt?

If no, it belongs in Channel B. This single question resolves every type below,
and — critically — it *permits* process narration whenever process narration is
what was asked for.

Two supporting questions when the first is ambiguous:

> Would this sentence survive if the deliverable were printed and handed to a
> stranger?

> Is this sentence about the subject, or about the making of the document?

## Taxonomy

### 1. Process narration

The model describing its own work.

> I've analyzed your document and identified three recurring themes.
> After reviewing the data, I found that...
> Let me break this down for you.

**Fix:** delete, and start at the finding. "Three themes recur." The analysis
happened; it does not need announcing. The reader assumes competent work unless
told otherwise.

### 2. Brief echo

The specification, read back.

> Here is a 500-word blog post in a professional tone for small business owners.
> Below is the executive summary you requested.

**Fix:** delete the sentence entirely and begin at the real first sentence of the
piece. Brief echo is almost always the *first* thing in a contaminated draft, and
almost always followed by the actual opening. Cut down to it.

### 3. Constraint recitation

Compliance, signalled.

> I avoided technical jargon, as requested.
> Note: kept under 500 words.
> I've used British spelling throughout.

**Fix:** move to Channel B if the operator needs confirmation; otherwise delete.
Meeting a constraint is not an achievement to report inside the artifact. If the
constraint was missed, that is a genuine Channel B note — say so there.

### 4. Persona leakage

The assigned role, worn visibly.

> As a seasoned copywriter with over 20 years of experience...
> Speaking as your financial analyst...

Source: `You are an expert copywriter` in the prompt. The persona was a steering
device. It is not a byline.

**Fix:** delete. The expertise should be visible in the quality of the writing,
not asserted in its first line. Exception: the deliverable genuinely has a
first-person author (a bio, a personal essay, a cover letter) — then the voice is
content, not leakage.

### 5. Scaffolding leakage

Template or rubric structure, shipped literally.

> **Hook:** Small businesses lose 30% of...
> **Body:** The main issue is...
> **CTA:** Get started today.

Also: the outline appearing as headings; `[INSERT STATISTIC]` placeholders;
section numbers from a template that the finished piece does not need; rubric
criteria as subheadings.

**Fix:** convert each label into a real heading if the document wants headings,
or delete the labels and let the prose run. The scaffolding was a thinking aid.
Thinking aids do not ship.

### 6. Source attribution nobody asked for

> According to the document you uploaded, revenue grew 12%.
> Based on the context you provided...
> From the files you shared, it appears that...

**Fix:** state the fact. "Revenue grew 12%." Where it came from is the operator's
own knowledge — they supplied it.

Do not confuse this with genuine citation. If the deliverable is a report that
cites sources for its reader, citation is content and stays. The test is whether
the attribution is *to the reader* or *to the operator*.

### 7. Structural throat-clearing

The document narrating its own shape.

> In this section, we will explore...
> This article will cover three main areas.
> First, let's define our terms. Then we'll look at...
> Now that we've established X, let's turn to Y.

**Fix:** delete and let the structure do its own work. Headings, paragraph
breaks, and order already tell the reader where they are. A document that
announces its own table of contents in prose is padding.

Mild transitional phrasing is fine. The line is between *guiding the reader* and
*describing the document*.

### 8. Self-assessment and offers

> This should give you a solid starting point.
> Feel free to let me know if you'd like me to adjust anything.
> I hope this captures what you were looking for.
> This is a comprehensive overview of...

**Fix:** delete from the deliverable. A brief offer to revise is legitimate
Channel B content in a conversational reply — put it there, once, and not inside
the artifact. Never grade your own output ("comprehensive", "detailed",
"thorough") — the reader decides that.

### 9. Wrappers

> Sure! Here's the post:
> Certainly. Below you'll find...
> ---
> Hope this helps!

**Fix:** delete both ends. If the deliverable needs an introduction in chat, one
short Channel B line does it.

## When meta-writing IS the deliverable

Do not strip these. In each case the process *is* the subject, and applying the
test correctly permits them — a reader who never saw the prompt still needs them.

- **Explanations of reasoning.** Asked to show your work, the work is the output.
- **Code review and audits.** "I checked X and found Y" is the finding format.
- **Status reports and progress updates.** The operator is the audience; there is
  no separate artifact.
- **Terminal and chat replies about a task.** Reporting what was changed in which
  file is the entire point.
- **Teaching and tutorials.** "First we'll set up the database, then..." is
  legitimate reader guidance, not throat-clearing.
- **Methodology sections.** In a research document, describing how the work was
  done is content.
- **Cover letters, bios, personal essays.** First person is the form.
- **Documents about AI, prompting, or writing process.** The subject matter
  legitimately includes the vocabulary of this file.

The failure mode of over-application is real: a model that strips all first
person and all process language produces cold, contextless replies and useless
code review. When in doubt, ask who the reader is. If the reader is the operator,
Channel A and Channel B are the same channel, and almost nothing needs moving.

## Judgement calls

**Length.** Cutting meta-writing shortens a draft, sometimes noticeably. Do not
backfill with invented content to restore a word count. If a hard count was
specified and the clean draft falls short, develop the actual subject or tell the
operator in Channel B. Never pad.

**Ambiguous requests.** "Write me a summary" is a deliverable. "Summarise what
you did" is a status report. When genuinely unclear which was meant, produce the
clean deliverable and put the alternative reading in Channel B — that is cheaper
to correct than the reverse.

**Partial contamination.** A single meta sentence inside an otherwise clean
paragraph gets cut in place. Do not rewrite the surrounding text to accommodate
the removal unless the paragraph no longer reads.
