# Compose Director — Explainer Templates Pipeline

## Customizations from base `animated-explainer/compose-director.md`

This file is forked from `skills/pipelines/animated-explainer/compose-director.md`.
Changes made for the `explainer-templates` pipeline:
- **Template-driven composition** — reads the active template's skeleton.html/style.css
- **Runtime determined by template** — each template declares its runtime (hyperframes default)
- **GSAP-driven text clips** — v2 `minimal` template reads scene data-* attributes at runtime
- **sync-timings.py patching works transparently** — GSAP JS reads timing from HTML attributes, not hardcoded values
- **TTS voice from template config** — narration.voice in template.yaml
- **SRT subtitle export** — from ASR word-level timestamps
- **Chinese-first** — narration is zh-CN; all subtitle handling assumes Chinese text
- **Zero cost** — all assets are free (stock photos, free music, Edge TTS); render is local HyperFrames

## When to Use

You are the Compositor for a generated explainer video. You have `edit_decisions` with the complete edit timeline and an `asset_manifest` with all file paths. Your job is to render the final video: build the composition using the active template's skeleton, run sync-timings.py for audio-text sync, and encode to the target format.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["edit"]["edit_decisions"]`, `state.artifacts["assets"]["asset_manifest"]` | What to render |
| Template config | `template.yaml` of selected template | Skeleton path, viewport, motion settings |
| Playbook | Active style playbook | Quality targets |
| Tools | `hyperframes_compose`, `audio_mixer` | Rendering + audio mix |

## Process

### Step 0: Read Template Config

Read the active template definition:
- Path: `config.templates[brief.template].file` (e.g., `templates/minimal/template.yaml`)
- Read the template's `skeleton.html` and `style.css`
- These define the structural layout, visual styling, and GSAP timeline patterns

The skeleton is the composition blueprint with placeholders. The compose-director's job is to:
1. Generate all placeholder content from `edit_decisions` + asset_manifest
2. Update animation param defaults in the JS CFG object to match template.yaml
3. Apply the template's CSS
4. Render, run sync-timings, and re-render

### Step 1: Verify Assets

Before rendering:

1. **Verify narration exists:** Check per-section narration files exist (concatenated into `assets/audio/narration.mp3`)
2. **Verify SRT subtitles exist:** Edge TTS generated `.srt` files alongside each narration section (via `--write-subtitles`)
3. **Concatenate per-section SRTs** into a master subtitle file:
   ```bash
   python scripts/merge_srt.py projects/<project>/assets/narration/*.srt > projects/<project>/assets/subtitles/master.srt
   ```
4. **Verify background music:** Check background music file exists
5. **Verify all image assets** from the manifest exist on disk
6. **Probe durations:**
   ```bash
   ffprobe -v error -show_entries format=duration -of csv=p=0 projects/<project>/assets/audio/narration.mp3
   ffprobe -v error -show_entries format=duration -of csv=p=0 projects/<project>/assets/music/background_music.mp3
   ```
   - Narration ±15% of target video duration
   - Music ≥ video duration (will be looped if needed)

### Step 1.5: Confirm Narrator Voice

Before building the composition, ask the user to confirm the narrator voice used for TTS:

> **Narrator voice:** `<voice_id>` (from `template.yaml` → `narration.voice`)
> The narration has already been generated with this voice. Do you want to proceed?
> - **Yes**: Continue to composition.
> - **No**: Specify a different voice ID, then return to **asset-director** to re-generate TTS assets with the new voice. Do NOT proceed with composition until new narration is generated.

**Implementation:**
```text
Show the user the voice ID from template.yaml. Ask for confirmation.

If they approve: continue to Step 2.
If they reject: ask for the new voice ID, update template.yaml's narration_voice field,
then STOP — the asset-director needs to re-run TTS generation.
```

### Step 1.6: Propose and Confirm Video Title

A title scene overlays the beginning of the video (large Chinese title + English subtitle, fading out after 3-5s). Propose a title based on the script content and ask the user to confirm:

1. **Derive the title from script** — read the script sections' `label` and `visual_concept` fields to identify the video's central theme.
2. **Propose a Chinese title** — 4-10 characters, impactful, summarizing the video's topic.
3. **Propose an English subtitle** — complementary translation or tagline.
4. **Ask the user to confirm:**

> **Proposed title:**
> - 中文: [Chinese title]
> - English: [English subtitle]
> 
> Do you approve this title?
> - **Yes**: Use the proposed title for the title scene.
> - **No**: Ask the user to provide their own title text (Chinese + English).

5. **Store the confirmed title** — pass the Chinese title and English subtitle to Step 2h for HTML generation.

**Example (for a trading psychology video):**
```
Script labels: "开场 — 概率的本质", "允许失败", "摆脱恐惧", "超然", "关注概率", "核心"
Theme: Trading psychology — learning detachment and embracing probability
→ 中文: "交易心理学"
→ English: "The Psychology of Trading"
```

### Step 2: Build Composition from Template Skeleton

**Workflow:**

1. **Create a HyperFrames project** (one per video):
   ```bash
   npx hyperframes init projects/<project>/hyperframes --template blank
   ```

2. **Copy the template's skeleton.html and style.css** into the HyperFrames project:
   - `skeleton.html` → `projects/<project>/hyperframes/index.html`
   - `style.css` → `projects/<project>/hyperframes/style.css`

#### Step 2a: Generate `{{TITLE}}`

Replace with the video title from the brief.

#### Step 2b: Generate `{{COMPOSITION_DURATION}}`

Total video duration in seconds (from `edit_decisions.total_duration`), formatted as a float with 3 decimal places (e.g., `50.700`).

#### Step 2c: Generate `{{BACKGROUND_IMAGES_HTML}}`

For each background image in the scene plan, generate one `<img>` element:

```html
<img id="bg-1" class="bg-img-layer" src="assets/images/scene-1-bg.jpg" alt="">
<img id="bg-2" class="bg-img-layer" src="assets/images/peak-bg.jpg" alt="" style="opacity:0">
<img id="bg-3" class="bg-img-layer" src="assets/images/scene-2-bg.jpg" alt="" style="opacity:0">
```

**Critical rules:**
- The FIRST `<img>` MUST NOT have `style="opacity:0"` — it is the initial visible background.
- ALL subsequent `<img>` elements MUST have `style="opacity:0"` — GSAP fades them in.
- `id` attributes must be `bg-1`, `bg-2`, ..., `bg-N` (1-indexed, matching scene order).
- There should be at least as many background images as there are text clips. Extra transition-only images are optional but recommended for visual variety.

#### Step 2d: Generate `{{SCENES_HTML}}`

For each scene in `edit_decisions`, generate one `<section>` containing per-sentence `<div class="sentence">` elements with proportional timing:

```html
<section id="scene-1" class="clip text-clip" data-start="0" data-duration="8.4" data-track-index="1">
  <div class="overlay"></div>
  <div class="scene-inner">
    <div class="sentence" data-t="0" data-dur-frac="0.226">市场是概率的，<span class="highlight">多变</span>的。</div>
    <div class="sentence" data-t="0.226" data-dur-frac="0.774">很多时候即使一切都作对了，但还是一样失败，<span class="highlight">这就是交易</span>。</div>
  </div>
</section>

<section id="scene-2" class="clip text-clip" data-start="8.5" data-duration="8.6" data-track-index="2">
  <div class="overlay"></div>
  <div class="scene-inner">
    <div class="sentence" data-t="0" data-dur-frac="1.0">很多人因为它带来的<span class="highlight">挫败感</span>而退出，除非你<span class="highlight">允许自己失败</span>，否则你很难在交易市场取得成功。</div>
  </div>
</section>
```

**Sentence timing calculation (proportional):**

Each sentence in `edit_decisions.timeline[i].sentences` has `start_offset` (seconds from scene start) and `duration_seconds`. Convert to proportional fractions:

```
scene_duration = scene.out_seconds - scene.in_seconds
t_fraction     = sentence.start_offset / scene_duration      → data-t
dur_fraction   = sentence.duration_seconds / scene_duration  → data-dur-frac
```

This proportional encoding ensures that when `sync-timings.py` corrects scene-level `data-start`/`data-duration`, sentence timing scales proportionally. No JS changes needed.

**Keyword highlighting rules:**

For each sentence, identify 1-3 thematically important keywords and wrap them in `<span class="highlight">KEYWORD</span>`:

1. **From script `visual_concept`**: Words/phrases that appear in both the sentence and the scene's `visual_concept` field are prime candidates.
2. **Domain-specific terms**: 2-4 character domain terms (e.g., 概率, 交易, 挫败感, 超然, 核心, 盈亏).
3. **Thematic emphasis**: The key concept the sentence is making a point about — usually the subject or object of the main clause.
4. **Target ~1-3 highlights per sentence**: Not every word, only the most meaningful terms.
5. **Match entire phrase when possible**: e.g., "允许自己失败" rather than just "失败".

**Critical rules:**
- `id` must be `scene-N` where N is 1-based.
- `class` must be exactly `clip text-clip` (both classes required for HyperFrames and GSAP).
- `data-start` = scene start time in seconds (float, from `edit_decisions.timeline[i].in_seconds`).
- `data-duration` = scene duration in seconds (float).
- `data-track-index` = alternating `1`/`2` starting with `1` (for z-ordering between overlapping scenes).
- Each sentence MUST be a `<div class="sentence">` with `data-t` and `data-dur-frac` attributes.
- All sentences MUST be wrapped in `<div class="scene-inner">...</div>`.
- Keywords MUST be wrapped in `<span class="highlight">keyword</span>`.
- DO NOT add `data-no-timeline` attribute (the v1 CSS-fade template used this — v2 GSAP MUST NOT).
- For single-sentence scenes: `data-t="0" data-dur-frac="1.0"`.
- **Title offset (CRITICAL — prevents title/body overlap):** If a title scene exists (confirmed in Step 1.6), scene-1's text sentences are automatically delayed by the title duration in the GSAP skeleton. You do NOT need to adjust scene-1's `data-start` — it stays at `0` so the background crossfade and narration audio remain synced. The skeleton reads `titleClip.dataset.duration` and shifts scene-1 sentence animations accordingly. However, ensure the title scene is placed AFTER `{{SCENES_HTML}}` in the HTML (so it renders on top with higher z-index).

#### Step 2e: Generate `{{NARRATION_DURATION}}`

Duration of `narration.mp3` from ffprobe, formatted as float (e.g., `49.536`).

#### Step 2f: Generate `{{BGM_HTML}}`

If BGM is enabled in the project config:

```html
<audio id="bgm" src="assets/music/background_music.mp3" data-start="0" data-duration="{{BGM_DURATION}}" loop data-track-index="98"></audio>
```

Use the ffprobe-probed BGM duration. If BGM is disabled, replace `{{BGM_HTML}}` with an empty string or a comment `<!-- no BGM -->`.

#### Step 2g: Update GSAP Timeline Config Parameters

The skeleton's JS includes a `CFG` object with animation defaults. Update each value to match the active template's `motion.gsap.*` config:

| CFG key | template.yaml path | Description |
|---------|-------------------|-------------|
| `zoomMax` | `motion.gsap.ken_burns.zoom_max` | Ken Burns max scale |
| `bgCrossfade` | `motion.gsap.ken_burns.crossfade_duration` | Background crossfade duration |
| `textEntryDuration` | `motion.gsap.text.entry.duration` | Text slide-in duration |
| `textExitDuration` | `motion.gsap.text.exit.duration` | Text fade-out duration |
| `textEntryY` | `motion.gsap.text.entry.y_offset` | Text slide-in y offset (px) |
| `sceneFadeIn` | `motion.gsap.text.scene.fade_in_duration` | Scene entry fade duration |
| `exitPad` | — (1.0 default) | Text exit starts `exitPad` seconds before scene end |

If the template doesn't specify a value, use the skeleton default.

#### Step 2h: Generate `{{TITLE_HTML}}`

If a title was confirmed in Step 1.6, generate the title scene HTML. The title overlays scene-1 initially and fades out after 4 seconds:

```html
<section id="title-scene" class="clip title-clip" data-start="0" data-duration="4.0" data-track-index="3">
  <div class="title-overlay"></div>
  <div class="title-content">
    <div class="title-main">交易心理学</div>
    <div class="title-sub">The Psychology of Trading</div>
  </div>
</section>
```

**Rules:**
- `data-duration`: 3.0-5.0 seconds (enough to read, adjust based on title length). Default: 4.0s.
- `data-track-index`: MUST be `3` (higher than the scene tracks 1/2, so it renders on top).
- `class`: MUST be `clip title-clip` (both classes required for HyperFrames and GSAP).
- The title scene shares the first background image (no separate bg needed — scene-1 is visible underneath).
- `<div class="title-main">`: Chinese title, 88px bold, centered.
- `<div class="title-sub">`: English subtitle, 36px light weight, centered, below title.
- If no title was confirmed, replace `{{TITLE_HTML}}` with an empty string.

### Step 3: Validate and Render (First Pass)

1. **Run validation:**
   ```bash
   npx hyperframes lint projects/<project>/hyperframes
   npx hyperframes validate projects/<project>/hyperframes
   ```
   Both must pass with zero errors before rendering.

2. **Render first pass (with estimated timing):**
   ```bash
   npx hyperframes render projects/<project>/hyperframes --output projects/<project>/renders/output.mp4
   ```

3. **Verify the render produced output:**
   ```bash
   ls -la projects/<project>/renders/output.mp4
   ffprobe -v quiet -print_format json -show_format -show_streams projects/<project>/renders/output.mp4
   ```
   - Video stream present
   - Audio stream present
   - Duration reasonable

### Step 4: Run sync-timings.py (Mandatory)

After the first HyperFrames render, sync-timings.py corrects all scene timing using ASR transcription.

> **Why this works with GSAP**: The skeleton's GSAP timeline JS reads `data-start` and `data-duration` from scene elements at runtime. sync-timings patches these exact attributes. On re-render, the timeline automatically uses corrected timing. No JS modification needed.

**Run it:**
```bash
python scripts/sync-timings.py projects/<project>/hyperframes
```

**Command options:**
| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview changes without modifying files |
| `--asr-json PATH` | Use pre-computed ASR JSON (skip re-transcription, for iteration) |
| `--narration PATH` | Custom narration path (default: `assets/audio/narration.mp3`) |
| `--html PATH` | Custom HTML path (default: `index.html`) |

**Expected output:**
- Timing correction report showing old → new start/duration values per scene
- Confidence score per scene (character-set Jaccard overlap with ASR)
- Low-confidence matches (< 30%) are flagged for manual review
- `index.html` is patched in-place with corrected `data-start`/`data-duration`

**Quality gate:**
- Check for any scene with `< 30%` confidence — these need manual timing review
- Verify total duration shift is reasonable

**Also: update `{{COMPOSITION_DURATION}}`** on `#root` to match the new total narration duration.

**Re-render with corrected timing:**
```bash
npx hyperframes render projects/<project>/hyperframes --output projects/<project>/renders/output.mp4
```

### Step 5: Generate SRT Subtitles

Generate SRT subtitles from the ASR word-level timestamps (produced by sync-timings or a separate Whisper transcription):

```python
from tools.analysis.transcriber import Transcriber
result = Transcriber().execute({
    'input_path': 'projects/<project>/assets/audio/narration.mp3',
    'model_size': 'base',
    'language': 'zh',
    'output_dir': 'projects/<project>/assets/subtitles/',
    'output_format': 'srt',
    'word_timestamps': True,
})
```

The resulting SRT file goes to `projects/<project>/assets/subtitles/master.srt`. This file should be included in the final render report.

### Step 6: Post-Render Self-Review (Mandatory)

After rendering, review your own output before presenting to the user.

**6a. Probe rendered file:**
```bash
ffprobe -v quiet -print_format json -show_format -show_streams rendered_video.mp4
```
- [ ] Video stream exists with correct resolution (1080×1920)
- [ ] Audio stream exists — if MISSING, STOP and fix
- [ ] Duration within ±5% of target
- [ ] File size is reasonable

**6b. Transcribe rendered audio:**
```python
from tools.analysis.transcriber import Transcriber
result = Transcriber().execute({
    'input_path': 'path/to/rendered_video.mp4',
    'model_size': 'base',
    'language': 'zh',
    'output_dir': 'path/to/review-frames',
})
```
- [ ] Audio has content (word count > 0)
- [ ] Word count ≥ 80% of script — if significantly less, audio is cut off

**6c. Visual inspection:**
- [ ] Background fills entire viewport without stretching
- [ ] Dark overlay applied for text readability
- [ ] Text centered and positioned correctly
- [ ] Highlighted keywords visibly different (color: #FFD93D)
- [ ] GSAP animation is smooth (Ken Burns zoom, text slide-in, crossfades)
- [ ] Background transitions sync with scene changes
- [ ] Only ONE text clip visible at a time

**6d. Present review to user:**
> **Post-render review for "[Video Title]":**
> **File:** [duration]s, [resolution], [file size]
> **Audio:** [Complete/Cut off]
> **Visuals:** [issues or "all scenes rendering correctly"]
> **sync-timings:** [report summary]
> **Subtitles:** [present/missing]
> **Issues found:** [list]
> **Recommendations:** [what to fix]

### Step 7: Build Render Report

Validate the render_report against the schema and persist via checkpoint. Include subtitle file path if generated.

### Step 8: Self-Evaluate

| Criterion | Question |
|-----------|----------|
| **Playability** | Does the video play without errors in a standard player? |
| **Duration accuracy** | Is actual duration within ±5% of target? |
| **Audio quality** | Is narration clear, music balanced, no clipping? |
| **Visual quality** | Are images sharp, transitions smooth, no artifacts? |
| **Subtitle accuracy** | Are subtitles present, readable, and synced? |
| **Animation quality** | Are GSAP animations smooth (no jank, pop-in, or incorrect timing)? |

If any dimension scores below 3, investigate and re-render.

## Common Pitfalls

- **Missing title scene (blocked)**: Every project MUST emit a title clip (Step 1.6 + Step 2h). If the composition starts straight into the hook with no title card, the project is incomplete — add `class="clip title-clip"` at `data-start="0"` with `data-duration` ≈ 3.0–4.0s and `data-track-index="3"` before rendering.
- **Missing `opacity:0` on subsequent bg images**: The initial `<img>` must NOT have `opacity:0`, all others MUST. Without this, all backgrounds are visible at once.
- **Missing `class="clip"` on scenes**: HyperFrames requires `class="clip"` for timeline registration. Missing it = scene never shows.
- **Missing `class="text-clip"` on scenes**: The GSAP selector `'.clip.text-clip'` won't match without it.
- **Adding `data-no-timeline`**: v2 GSAP template MUST NOT use `data-no-timeline`. That was the v1 CSS-fade convention.
- **Missing asset files**: Always verify every referenced file exists before starting the render.
- **Adding animations beyond template**: The template's `motion.*` section defines what animation is allowed. Do not add custom GSAP animations beyond what the skeleton provides.
- **Audio sync drift**: sync-timings.py corrects this. Check confidence scores.
- **sync-timings.py low confidence**: If character overlap is below 30%, the timing correction may be wrong. Manually adjust.
- **Chinese font rendering**: Ensure Noto Sans SC loads via Google Fonts `<link>` in `<head>`.
- **Template skeleton not found**: Verify the template's `files.skeleton` path exists. If missing, fall back to inline generation.
- **GSAP loaded but animations not running**: Check that `cdn.jsdelivr.net` is accessible and GSAP loads before the timeline script runs.
