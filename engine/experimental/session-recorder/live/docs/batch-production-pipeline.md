# Batch production: planning a large course of clips

This tool records one clip at a time. Producing a *course* — dozens or
hundreds of clips that need to cohere, stay on-topic, and actually finish
running — needs a planning layer on top of `record-session`. This doc
captures a pipeline reported in
[htlin222/claude-session-recorder#2](https://github.com/htlin222/claude-session-recorder/issues/2):
a 124-clip, ~10-hour, ELI5 course on Claude Code, produced 1:1 against every
page of the official docs (minus the code-facing Agent SDK) in roughly nine
hours of wall-clock recording. It is documented here as a reusable pattern,
not a script bundled with the repo — adapt the stage boundaries to your own
course.

## The four stages

### 1. Research (parallel, one agent per doc-cluster)

Split the source material (e.g. a docs site) into clusters and fan out one
agent per cluster. Each agent fetches its group of pages and writes a
research note per page containing:

- an ELI5 analogy for the concept,
- every command/flag mentioned on the page (needed for 1:1 completeness
  later),
- tips and gotchas, and
- a sketch of a demo that can run in a throwaway `/tmp` sandbox with no
  cloud credentials.

Running research in parallel, per-cluster, keeps each agent's context small
and focused instead of one agent trying to hold the whole doc set in its head.

### 2. Syllabus + coverage matrix

From the research notes, lay out the course structure — e.g. N modules of
~10 clips each — with **every clip mapped to a specific source doc URL**.
Alongside the syllabus, keep a separate **coverage matrix** that
cross-references every doc slug against the clip that covers it, so nothing
is silently dropped. Where several source pages don't map 1:1 to a clip
(e.g. three separate CI provider pages folded into one "CI 101" clip), mark
that explicitly in the matrix rather than letting pages quietly disappear.

The coverage matrix is what makes a large batch auditable: at any point you
can grep it for doc slugs with no clip, or clips with no `_comment` back-link
(see the lint below).

### 3. Script-writing (parallel, one agent per module)

Fan out again, this time one agent per module, each producing:

- a teaching card (learning goals, ELI5 analogy, step-by-step demo, tips,
  common mistakes), and
- the actual `script.json` for each of its ~10 clips (see
  `script.example.json`, `script.mixed.json` etc. in this directory for the
  schema this tool expects).

All script-writing agents follow one written **style guide**, so the course
reads as one voice instead of N clashing ones:

- **Narration in the target language, `prompt`s in English** — the model is
  more reliable executing English prompts even when the course is narrated
  in another language.
- **Narration budget calibrated empirically**, not guessed: roughly
  **550–750 characters of narration for a ~5-minute clip**, after this
  tool's freeze-frame splicing settles the final runtime. Measure a handful
  of real clips before locking the number in for 124 of them.
- **2–4 turns per clip**, each turn a small, visibly-completable unit of
  work (see [lesson 3](#3-keep-each-turns-real-workload-small) on why turn
  size matters beyond pacing).
- **Every `prompt` runnable in a brand-new `/tmp` sandbox with no real cloud
  credentials.** For topics that are inherently cloud/enterprise-only
  (Bedrock, Vertex, gateways, managed settings, ...), the demo pattern
  becomes "ask Claude to generate the example config file and explain it
  field-by-field" rather than trying to actually connect to anything.
- **A `jq`-based lint script** enforcing, per `script.json`:
  - valid JSON,
  - required fields present,
  - 2–4 turns,
  - narration length in range, and
  - a doc-URL reference embedded in a `_comment` field, so every clip is
    traceable back to the coverage matrix.

### 4. Production

A small wrapper script iterates the script tree and, per clip, calls:

```bash
record-session <sandbox-dir> <script.json>
```

On success it copies only the final `session_panel.mp4` / `.srt` out of the
(credential-bearing) sandbox into a permanent `output/` tree — the sandbox
itself never leaves `/tmp`. The wrapper skips a clip whose output already
exists, which is what makes the next section possible.

## Lessons learned

These four points are the ones worth internalizing before starting a batch
of this size, not after.

#### 1. Write the lint before you write the scripts, not after

Character-count drift and missing fields are easy to introduce across a
large batch of hand- or agent-authored `script.json` files, and easy to
catch mechanically. Writing the `jq` lint (schema + turn count + narration
length + doc-URL traceability) *before* the parallel script-writing agents
run means every one of the 124 scripts is validated as it's produced,
instead of discovering drift after the fact across all of them.

#### 2. Treat "does this prompt fire a Stop event" as a real authoring constraint

This is not an edge case to handle later — it determines whether a turn can
be recorded at all. Bare local-command prompts and literal feature-trigger
keywords (for example, writing the word "ultraplan" in a prompt that's
*about* the ultraplan feature) are surprisingly easy to reach for when
writing "teach the concept" scripts, and they silently produce turns that
never complete. See the concrete bugs filed from this production run in
[htlin222/claude-session-recorder#1](https://github.com/htlin222/claude-session-recorder/issues/1)
(quote escaping, native menus, local-only commands, prompt suggestions) —
review that list before finalizing a style guide for prompt authoring.

#### 3. Keep each turn's *real* workload small

A turn that asks Claude to spin up a multi-agent workflow, or do careful
research/validation work, can legitimately run past a fixed wait timeout —
that's not a bug in the recorder, it's the turn taking on too much scope.
Explicitly telling Claude "keep it quick, skip extra validation for this
demo" in the prompt earns back a lot of reliability, and keeps clip runtimes
inside the narration budget from the style guide.

#### 4. The output-dir-skip-check pattern makes long batches recoverable

Structure the production wrapper so it only copies output on success and
checks for existing output before re-running a clip. Over a long batch (in
the reported run, ~15 hours of wall-clock time with the environment killing
the process more than a dozen times), every restart then just picks up where
it left off with zero manual bookkeeping — the wrapper is the checkpoint,
not a human tracking a spreadsheet.

## Summary

| Stage | Fan-out | Output |
| --- | --- | --- |
| 1. Research | one agent per doc-cluster | per-page research notes (ELI5 analogy, commands/flags, gotchas, demo sketch) |
| 2. Syllabus + coverage matrix | single pass | modules → clips, each mapped to a doc URL; a matrix cross-referencing every doc slug |
| 3. Script-writing | one agent per module | teaching card + `script.json` per clip, enforced by a `jq` lint |
| 4. Production | wrapper script over `record-session` | `output/<clip>/session_panel.mp4` + `.srt`, resumable |

This pattern scales the planning and authoring work horizontally (parallel
agents per cluster/module) while keeping the actual recording step — the one
that must run `claude` for real — sequential, resumable, and mechanically
verified before it ever runs.
