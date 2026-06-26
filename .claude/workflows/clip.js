export const meta = {
  name: 'clip',
  description: 'Make a 4–6 min CLI-education clip from ./material (or an instruction) using the clip/ render engine; final lands in ./<slug>/',
  whenToUse: 'Produce a narrated CLI teaching video. Reads ./material/ and/or the /clip <instruction> arg, authors a lesson under clip/lessons/<slug>/, renders via the clip/ engine, copies the finished mp4/srt/html into ./<slug>/.',
  phases: [
    { title: 'Design', detail: 'read material + instruction, plan a ~5 min lesson' },
    { title: 'Author', detail: 'write the lesson, run build, fit duration to 4–6 min (loop)' },
    { title: 'Render', detail: 'setup env, vhs the terminal, overlay panel + transitions' },
    { title: 'Verify', detail: 'check A/V sync; auto-heal desync via guided clears (loop)' },
    { title: 'Deliver', detail: 'copy mp4/srt/html into ./<slug>/ + manifest' },
  ],
}

// ---- shared context handed to every agent (they don't see this conversation) ----
const ENGINE = `
RENDER ENGINE (do not modify its source): the repo root holds clip/, a
tool-agnostic CLI-education video engine. CWD for every command is the repo root.

A *lesson* is the only thing you create. It lives in  clip/lessons/<slug>/  and is:
  lesson.py  - defines three module names and nothing tool-specific:
                 from lesson import S, R, CLR        # provided by clip/src/lesson.py
                 SLUG  = "<slug>"                     # kebab-case; names all outputs
                 TITLE = "<human title>"
                 SCRIPT = [ ...timeline... ]
  setup.sh   - bash '#!/usr/bin/env bash' + 'set -euo pipefail'; (re)creates this
               lesson's throwaway demo env in its PER-SLUG workspace. Start with:
                 DEMO="\${CLIP_DEMO:-$(cd "$(dirname "$0")/../../intermediate" && pwd)/$(basename "$(dirname "$0")")}"
                 mkdir -p "$DEMO"; cd "$DEMO"
               then 'rm -rf <yourdirs>' and recreate them. Must be idempotent and
               self-contained. Make any file the commands need (sample trees, a
               >1MB file for size demos, backdated timestamps for time demos, etc).

SCRIPT builders (imported from lesson):
  S("一句旁白")                         one continuous-narration sentence (zh-TW)
  R("the command to run")               a command typed + executed on screen
  CLR(key=..., hero=..., toks=[...])    opens a scene + its right-hand explain panel
      key  = one-line headline (zh-TW). A bare CLR(key=...) with no hero is a valid
             intro scene (folder tour etc).
      hero = the command to dissect token by token (must equal a following R()).
      toks = [(substr, "註解(zh-TW)", role), ...] revealed as each token finishes
             typing. role -> colour: "ord"=ordinary flag, "star"=the scene's KEY
             flag/idea, "path"=operands/paths/args.

PLATFORM (this renders on macOS): many coreutils here are BSD/variant builds that
differ from Linux/GNU — e.g. \`sed\` is BSD sed (\\w \\b \\+ and \\t/\\n in
replacements don't work, \`-i\` differs), \`awk\` is one-true-awk, \`grep\` may be
ugrep, \`date\`/\`stat\` differ. If a learner on Linux would see DIFFERENT output
than what renders here, that's a defect. So either (a) teach the GNU variant
explicitly — \`gsed\`/\`gawk\`/\`gdate\` (brew gnu-sed / gawk / coreutils), noting
in the intro that on Linux it's the bare name — or (b) restrict strictly to the
identical POSIX subset. Quick-check a doubtful command both ways before relying on
its output. Never show output that would differ on Linux without flagging it.

HARD RULES (the build will reject or mis-sync otherwise):
  1. toks are listed LEFT-TO-RIGHT as they appear in hero; each substr must be
     findable in hero in that order (no overlaps).
  2. Every "star"/"ord" token's flag text MUST appear VERBATIM in one of that
     scene's S() narration sentences, so the panel reveal lands in typing-sync.
     (e.g. a scene teaching -name must have an S() sentence containing "-name".)
  3. The narration is ONE flowing voice: write S() sentences that connect, and
     keep them as complete sentences ending in 。！？ so edge-tts splits them 1:1
     with your S() list. A mismatch makes build.py print "cue/sentence mismatch"
     and refuse to write the tape — if you see that, fix sentence boundaries.

Pattern per command scene (mirror clip/lessons/rsync/lesson.py and find/lesson.py):
  CLR(key="...", hero="cmd --flag X", toks=[("cmd-or-arg","...","path"),
       ("--flag","...","star")]),
  S("引入這個情境的一句話。"),
  S("這次用 --flag 做某事的解說句（句中要出現 --flag）。"),
  R("cmd --flag X"),
  S("看結果，總結這個情境的一句話。"),

ENGINE COMMANDS (run from repo root; <slug> is your lesson slug):
  # one-time venv for the panel renderer (skip if clip/.venv exists)
  ( cd clip && uv venv .venv && uv pip install --python .venv/bin/python pillow numpy )
  # Every step is PER-SLUG (workspace = clip/intermediate/<slug>) so runs are
  # parallel-safe. LESSON=<slug> picks the slug for build/overlay/setup.
  # 1) narration + tape + timeline
  ( cd clip && LESSON=<slug> python3 src/build.py )      # prints "predicted total = Xs"
  # 2) build env + render terminal (vhs runs INSIDE the per-slug workspace)
  ( cd clip && LESSON=<slug> bash src/setup_dirs.sh )
  ( cd clip/intermediate/<slug> && vhs demo.tape )      # -> clip/intermediate/<slug>/terminal.mp4
  # 3) composite panel + transitions + fades
  ( cd clip && LESSON=<slug> .venv/bin/python src/overlay.py )   # -> clip/dist/<slug>.mp4 + .srt

DURATION CALIBRATION: build's "predicted total" is the narration length; overlay
then adds intro/holds/transitions (~+1s per scene, ~+13s total for a 5–6 min clip).
The rsync lesson = 27 S() sentences / 6 command scenes -> ~140s, so a command-scene
block is ~23s and a sentence ~5s. The exact per-run TARGET WINDOW is given below.
`.trim()

const PLAN = {
  type: 'object', additionalProperties: false,
  required: ['slug', 'title', 'audience', 'topic_summary', 'scenes', 'target_minutes'],
  properties: {
    slug: { type: 'string', description: 'kebab-case, e.g. "git-rebase"' },
    title: { type: 'string' },
    audience: { type: 'string' },
    topic_summary: { type: 'string', description: 'what the clip teaches + where it came from (material vs instruction)' },
    target_minutes: { type: 'number' },
    scenes: {
      type: 'array',
      description: 'ordered scenes incl. optional intro; aim 12–16 command scenes for ~5 min',
      items: {
        type: 'object', additionalProperties: false,
        required: ['key', 'hero', 'teaches'],
        properties: {
          key: { type: 'string', description: 'panel headline (zh-TW)' },
          hero: { type: 'string', description: 'command, or "" for an intro/tour scene' },
          teaches: { type: 'string', description: 'the key flag/idea (the star token)' },
        },
      },
    },
  },
}

const FIT = {
  type: 'object', additionalProperties: false,
  required: ['build_ok', 'predicted_sec', 'narration_sentences', 'command_scenes', 'in_range', 'adjustment', 'error'],
  properties: {
    build_ok: { type: 'boolean', description: 'build.py wrote demo.tape + timeline.json without a cue/sentence mismatch' },
    predicted_sec: { type: 'number', description: 'the "predicted total" build.py printed (0 if build failed)' },
    narration_sentences: { type: 'integer' },
    command_scenes: { type: 'integer' },
    in_range: { type: 'boolean', description: 'predicted_sec within 255–345' },
    adjustment: { type: 'string', description: 'what you changed this pass (or "initial draft")' },
    error: { type: ['string', 'null'] },
  },
}

const RENDER = {
  type: 'object', additionalProperties: false,
  required: ['ok', 'final_mp4', 'final_srt', 'final_duration_sec', 'error'],
  properties: {
    ok: { type: 'boolean' },
    final_mp4: { type: 'string', description: 'path to clip/dist/<slug>.mp4 (or "" on failure)' },
    final_srt: { type: 'string' },
    final_duration_sec: { type: 'number' },
    error: { type: ['string', 'null'] },
  },
}

const SYNC = {
  type: 'object', additionalProperties: false,
  required: ['verdict', 'structural_synced', 'narration_fits', 'on_target', 'final_sec', 'jcut_applied', 'jcut_total', 'jcut_mean_sec', 'jcut_clips', 'voice_overruns', 'min_gap_sec', 'fix_applied', 'reasons', 'error'],
  properties: {
    verdict: { type: 'string', enum: ['PASS', 'FAIL_FIXABLE', 'FAIL'] },
    structural_synced: { type: 'boolean', description: 'every scene locked to a real terminal clear (not fallback)' },
    narration_fits: { type: 'boolean', description: 'finished video contains the whole narration (voice not cut)' },
    on_target: { type: 'boolean' },
    final_sec: { type: 'number' },
    jcut_applied: { type: 'integer', description: 'transitions that got a J-cut (from VERIFY_JSON)' },
    jcut_total: { type: 'integer', description: 'total transitions' },
    jcut_mean_sec: { type: 'number', description: 'mean applied J-cut lead' },
    jcut_clips: { type: 'integer', description: 'incoming J-cuts that overran the previous narration (must be 0)' },
    voice_overruns: { type: 'integer', description: "scenes whose OWN voice runs into the next clip — too little still-hold (must be 0)" },
    min_gap_sec: { type: 'number', description: 'smallest silent gap before any transition (should be >= ~HOLD)' },
    fix_applied: { type: 'boolean', description: 'guided-clears override was applied and overlay re-run' },
    reasons: { type: 'string', description: 'the human verdict line explanation, or "ok"' },
    error: { type: ['string', 'null'] },
  },
}

const DELIVER = {
  type: 'object', additionalProperties: false,
  required: ['ok', 'output_dir', 'files', 'error'],
  properties: {
    ok: { type: 'boolean' },
    output_dir: { type: 'string' },
    files: { type: 'array', items: { type: 'string' } },
    error: { type: ['string', 'null'] },
  },
}

// instruction passed as `/clip <instruction>`; may be a plain string or an object
const instruction = (typeof args === 'string' && args.trim()) ? args.trim()
  : (args && args.instruction) ? String(args.instruction) : ''
// target length: args.target_minutes (object), else a "<n> min(ute)" in the text,
// else default 5. The window is on build's PREDICTED total; overlay adds ~13s, so
// predicted ~ targetSec-15 centers the FINAL video on the target.
const _minMatch = instruction.match(/(\d+(?:\.\d+)?)\s*min/i)
const targetMin = (args && Number(args.target_minutes)) ? Number(args.target_minutes)
  : (_minMatch ? Number(_minMatch[1]) : 5)
const targetSec = Math.round(targetMin * 60)
const LO = targetSec - 30, HI = targetSec - 5            // predicted-total window
const sceneEst = Math.max(6, Math.round((targetSec - 40) / 23))   // ~23s per block
const DUR = `TARGET WINDOW for this run: aim build's "predicted total" in ${LO}–${HI}s `
  + `so the FINAL video lands at ~${targetMin} min (~${targetSec}s). That's roughly `
  + `${sceneEst-2}–${sceneEst+2} command scenes plus an intro tour.`

// ---------------------------------------------------------------- Design
phase('Design')
const plan = await agent(`
You are designing a CLI-education video lesson.

${ENGINE}

INPUTS:
- Direct instruction (may be empty): ${instruction ? JSON.stringify(instruction) : '(none)'}
- Material folder: read every file under ./material/ EXCEPT README.md (use ls/Read;
  it may be empty). Treat it as source material to teach from.
- If both exist, the instruction sets the topic/angle and material is supporting
  detail. If only material exists, derive the topic from it. If neither has usable
  content, pick a genuinely useful CLI topic and say so in topic_summary.

${DUR}

Produce a lesson PLAN for that length. Choose a kebab-case slug. Each scene teaches
ONE key flag/idea (the future "star" token). Order scenes from simplest/safest to
most advanced; put any destructive command late and flag it. Set target_minutes to
${targetMin}. Do NOT write files yet — just the plan.
`.trim(), { schema: PLAN, phase: 'Design', label: 'design lesson' })

if (!plan) return { ok: false, stage: 'Design', error: 'design agent returned nothing' }
const slug = plan.slug
log(`designed "${slug}" — ${plan.scenes.length} scenes, target ${plan.target_minutes}min`)

// ---------------------------------------------------------------- Author + fit loop
phase('Author')
let fit = null
for (let attempt = 1; attempt <= 6; attempt++) {
  const first = attempt === 1
  const mid = Math.round((LO + HI) / 2)
  const gap = fit ? mid - fit.predicted_sec : 0          // +short / -over
  const nScenes = Math.max(1, Math.round(Math.abs(gap) / 23))   // ~23s per scene
  const nSent = Math.max(1, Math.round(Math.abs(gap) / 5))      // ~5s per sentence
  fit = await agent(`
${first ? 'Author' : 'Adjust'} the lesson "${slug}" so build.py's predicted total
lands in ${LO}–${HI} seconds.

${ENGINE}

${DUR}

PLAN (from the design phase):
${JSON.stringify(plan, null, 2)}

${first ? `
Create both files now:
  clip/lessons/${slug}/lesson.py   (SLUG="${slug}", TITLE, SCRIPT per the plan)
  clip/lessons/${slug}/setup.sh    (chmod +x it; build whatever env the commands need)
Write natural, flowing zh-TW narration. Obey the THREE HARD RULES exactly.
` : `
A previous pass built at ${fit ? fit.predicted_sec : '?'}s; target is ${LO}–${HI}s
(centre ~${mid}s), so you are ${Math.abs(gap)}s ${gap > 0 ? 'SHORT' : 'OVER'}.
${gap > 0
  ? `GROW by roughly that much: ADD about ${nScenes} more command scene(s) (~23s each)
     OR ${nSent} more narration sentences. Don't be timid — undershooting wastes a
     whole attempt; aim to overshoot ${mid}s slightly rather than creep up.`
  : `TRIM by roughly that much: DROP/shorten about ${nScenes} command scene(s) or
     ${nSent} narration sentences.`}
Keep the HARD RULES intact. If the last build printed a "cue/sentence mismatch", fix
sentence boundaries (each S() must be one complete sentence ending in 。！？) so the
count matches, then rebuild.
`}

Then run, from the repo root:
  ( [ -d clip/.venv ] || ( cd clip && uv venv .venv && uv pip install --python .venv/bin/python pillow numpy ) )
  ( cd clip && rm -f intermediate/audio/${slug}.mp3 intermediate/audio/${slug}.srt; LESSON=${slug} python3 src/build.py )
Read the printed "predicted total = Xs, narration = Ys, N sentences, M panels"
line. Report it. (Deleting the cached audio forces re-synth after you edit
narration — do it every pass.) Do NOT run vhs/overlay; that's the next phase.
`.trim(), { schema: FIT, phase: 'Author', label: `author ${slug} #${attempt}` })

  if (!fit) return { ok: false, stage: 'Author', slug, error: 'author agent returned nothing' }
  const inRange = fit.predicted_sec >= LO && fit.predicted_sec <= HI   // authoritative
  log(`attempt ${attempt}: build_ok=${fit.build_ok} predicted=${fit.predicted_sec}s (window ${LO}-${HI}) scenes=${fit.command_scenes}`)
  if (fit.build_ok && inRange) break
}

if (!fit.build_ok) return { ok: false, stage: 'Author', slug, error: fit.error || 'build never succeeded' }

// ---------------------------------------------------------------- Render
phase('Render')
const render = await agent(`
Render the already-authored, duration-fitted lesson "${slug}" to a finished video.

${ENGINE}

The lesson files exist and build.py already produced clip/intermediate/demo.tape
and timeline.json for this slug (predicted ${fit.predicted_sec}s). Start a fresh
build log, then run each step teeing into it (the log is bundled into the product):
  : > clip/dist/${slug}.build.log
  ( cd clip && LESSON=${slug} bash src/setup_dirs.sh )              2>&1 | tee -a clip/dist/${slug}.build.log
  ( cd clip/intermediate/${slug} && vhs demo.tape )                 2>&1 | tee -a clip/dist/${slug}.build.log
  ( cd clip && LESSON=${slug} .venv/bin/python src/overlay.py )     2>&1 | tee -a clip/dist/${slug}.build.log

Then confirm clip/dist/${slug}.mp4 and clip/dist/${slug}.srt exist and probe the
mp4 duration with ffprobe. If vhs or ffmpeg errors, read the error, fix the
environment cause if you can (e.g. missing tool, bad setup.sh path) and retry once;
otherwise report the error verbatim. Report the real final duration.
`.trim(), { schema: RENDER, phase: 'Render', label: `render ${slug}` })

if (!render || !render.ok) return { ok: false, stage: 'Render', slug, error: (render && render.error) || 'render failed' }
log(`rendered ${slug}: ${render.final_duration_sec}s`)

// ---------------------------------------------------------------- Verify (sync loop)
phase('Verify')
let sync = null
for (let vattempt = 1; vattempt <= 3; vattempt++) {
  sync = await agent(`
Verify the audio↔video sync of the finished clip "${slug}", and auto-heal it if
it desynced. The pipeline ships src/verify_sync.py (the measurable signal) and
overlay.py honors a guided-clears override. Run from the repo root:

  ( cd clip && .venv/bin/python src/verify_sync.py --slug ${slug} --target-sec ${targetSec} --tol-sec 60 --write-override ) 2>&1 | tee -a clip/dist/${slug}.build.log

Read its output: a line "[${slug}] PASS|FAIL_FIXABLE|FAIL: ..." and a machine line
"VERIFY_JSON {...}". Then:
  - PASS  -> nothing to do; report it.
  - FAIL_FIXABLE -> it wrote intermediate/${slug}/clears_override.json (guided
      clears that fix the scene count). RE-COMPOSITE without re-running vhs:
        ( cd clip && LESSON=${slug} .venv/bin/python src/overlay.py )             2>&1 | tee -a clip/dist/${slug}.build.log
      then RE-VERIFY to confirm it's now in sync:
        ( cd clip && .venv/bin/python src/verify_sync.py --slug ${slug} --target-sec ${targetSec} --tol-sec 60 ) 2>&1 | tee -a clip/dist/${slug}.build.log
      Report the FINAL verdict after re-verify. Set fix_applied=true.
  - FAIL (not fixable: narration cut, or no guided solution) -> do NOT loop blindly;
      report the reasons verbatim so the caller can decide.

Parse the final VERIFY_JSON for your structured fields. reasons = the human line's
explanation (or "ok"). final_sec = its final_sec. Copy jcut_applied, jcut_total,
jcut_mean_sec, jcut_clips, voice_overruns and min_gap_sec straight from VERIFY_JSON.
Both jcut_clips AND voice_overruns MUST be 0: jcut_clips = the incoming J-cut talks
over the previous voice; voice_overruns = a scene's OWN voice runs into the next
clip (too little still-hold). Either is a defect, not a PASS — report it in reasons.
`.trim(), { schema: SYNC, phase: 'Verify', label: `verify ${slug} #${vattempt}` })

  if (!sync) { sync = { verdict: 'FAIL', reasons: 'verify agent returned nothing', structural_synced: false, narration_fits: false, on_target: false, final_sec: render.final_duration_sec, fix_applied: false, error: 'no result' }; break }
  log(`verify ${vattempt}: ${sync.verdict} synced=${sync.structural_synced} narration_fits=${sync.narration_fits} final=${sync.final_sec}s`)
  if (sync.verdict === 'PASS') break
  if (sync.verdict === 'FAIL_FIXABLE' && sync.fix_applied) continue   // tried; loop re-checks
  break                                                               // FAIL or gave up
}
const syncOk = !!(sync && sync.verdict === 'PASS')
if (!syncOk) log(`⚠ sync not PASS for ${slug}: ${sync ? sync.reasons : 'unknown'} — delivering with a flag`)

// ---------------------------------------------------------------- Deliver
phase('Deliver')
const deliver = await agent(`
Package the finished clip "${slug}" into its own product folder at the repo root.

Do this from the repo root:
  mkdir -p ${slug}
  cp clip/dist/${slug}.mp4 ${slug}/${slug}.mp4
  cp clip/dist/${slug}.srt ${slug}/${slug}.srt
  # offline HTML player (best-effort; skip if the generator is missing)
  python3 ~/.claude/skills/agent-demo-recorder/scripts/gen_html.py \\
      clip/dist/${slug}.mp4 -o ${slug}/${slug}.html || true
  # freeze this render's provenance into ${slug}/provenance/ — clip/intermediate/
  # is SHARED scratch the next build overwrites, so without this the clip becomes
  # unreproducible. Writes timeline/sync/jcut reports, verify.json (the 5 gates),
  # a config snapshot, terminal.mp4 + narration.mp3, the lesson source, build.log
  # and PROVENANCE.md. (Folder is "provenance/" not "build/" — "build/" is in most
  # global gitignores.)
  ( cd clip && .venv/bin/python src/bundle.py --slug ${slug} --target-sec ${targetSec} --tol-sec 60 )

Then write ${slug}/manifest.md with: the title (${JSON.stringify(plan.title)}),
audience, a one-paragraph summary, the scene list (key + hero command), the final
duration (${render.final_duration_sec}s), an **A/V sync** line stating
"${syncOk ? `sync verified (PASS) — J-cut on ${sync.jcut_applied}/${sync.jcut_total} transitions, mean ${sync.jcut_mean_sec}s; min gap ${sync.min_gap_sec}s; 0 voice overruns` : 'SYNC NOT VERIFIED — ' + (sync ? sync.reasons : 'unknown') + ' (review before publishing)'}",
a **Provenance** line noting that ${slug}/provenance/ holds the frozen record of
this render (timeline/sync/jcut reports, verify.json, config snapshot, terminal.mp4
+ narration.mp3, lesson source, build.log) and that provenance/PROVENANCE.md explains
how to re-composite from it without re-running vhs; and a note that the canonical source
lesson lives in clip/lessons/${slug}/ and a full rebuild is
\`( cd clip && LESSON=${slug} python3 src/build.py && LESSON=${slug} bash src/setup_dirs.sh ) && ( cd clip/intermediate/${slug} && vhs demo.tape ) && ( cd clip && LESSON=${slug} .venv/bin/python src/overlay.py )\`.

List every file you placed in ${slug}/ (including the provenance/ bundle's contents).
`.trim(), { schema: DELIVER, phase: 'Deliver', label: `deliver ${slug}` })

if (!deliver || !deliver.ok) return { ok: false, stage: 'Deliver', slug, error: (deliver && deliver.error) || 'deliver failed' }

return {
  ok: true,
  slug,
  title: plan.title,
  output_dir: deliver.output_dir,
  files: deliver.files,
  predicted_sec: fit.predicted_sec,
  final_duration_sec: render.final_duration_sec,
  command_scenes: fit.command_scenes,
  sync_ok: syncOk,
  sync_verdict: sync ? sync.verdict : 'UNKNOWN',
  sync_reasons: sync ? sync.reasons : 'verify did not run',
}
