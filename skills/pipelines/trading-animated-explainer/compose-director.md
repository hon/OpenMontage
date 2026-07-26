# Compose Director — Trading Explainer Pipeline

## Customizations from base `animated-explainer/compose-director.md`

This file is forked from `skills/pipelines/animated-explainer/compose-director.md`.
Changes made for the `trading-animated-explainer` pipeline:
- **Runtime locked to HyperFrames** — all Remotion-specific steps removed; only HyperFrames path remains
- **Edge TTS narration assumed** — audio comes from Edge TTS, subtitles from `--write-subtitles` SRT output
- **sync-timings.py mandatory** — post-render ASR-driven timing correction patches `index.html` data-start/data-duration
- **No CaptionOverlay, no WhisperX** — subtitles generated via Edge TTS SRT, sync-corrected by sync-timings.py
- **Chinese-first** — narration is zh-CN; all subtitle handling assumes Chinese text
- **Zero cost** — all assets are free (stock photos, free music, Edge TTS); render is local HyperFrames
- **Portrait 9:16 (mobile竖屏)** — viewport 1080×1920 instead of 1920×1080; background images sourced as portrait; only portrait media profiles used
- **Simple template mode (no animations)** — no GSAP kinetic typography, no chart animations, no Ken Burns. Output is a fixed-layout template: background image/video fills screen, one sentence fades in at a time. Only background and text change between runs.

## When to Use

You are the Compositor for a generated trading explainer video. You have `edit_decisions` with the complete edit timeline and an `asset_manifest` with all file paths. Your job is to render the final video: build the HyperFrames composition, run sync-timings.py for audio-text sync, and encode to the target format.

This is the last technical stage before the video exists as a playable file. Everything converges here.

## Runtime (locked — `render_runtime: hyperframes`)

This pipeline ALWAYS renders via HyperFrames. Do NOT check `edit_decisions.render_runtime` for branching — it is always `"hyperframes"`.

1. Call `hyperframes_compose` (via `video_compose` or directly) with the `edit_decisions` and `asset_manifest`
2. Read the HyperFrames skills for detailed workflow:
   - `.agents/skills/hyperframes/SKILL.md` — entry point, composition contract
   - `.agents/skills/hyperframes-core/SKILL.md` — HTML structure, data-start/data-duration, tracks
   - `.agents/skills/hyperframes-cli/SKILL.md` — CLI dev loop: init, lint, validate, render
   - `.agents/skills/hyperframes-media/SKILL.md` — audio handling, transcription, caption authoring
   
   **Note**: HyperFrames animation skills (hyperframes-animation) are NOT needed. This pipeline uses simple CSS fades only — no GSAP timelines or scene transitions.
3. Run `hyperframes lint && hyperframes validate` before render — both must pass before final delivery
4. After render, run `sync-timings.py` (see Step 5) to correct all timing from ASR transcription

`final_review.checks.promise_preservation.render_runtime_used` must be `"hyperframes"` and `runtime_swap_detected` must be `false`.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["edit"]["edit_decisions"]`, `state.artifacts["assets"]["asset_manifest"]` | What to render |
| Playbook | Active style playbook | Quality targets |
| Tools | `video_compose`, `audio_mixer` | Rendering capabilities |
| Media profiles | `lib/media_profiles.py` | Output format specs (resolution, codec, bitrate) |

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/render_report.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["edit"]["edit_decisions"]`, `state.artifacts["assets"]["asset_manifest"]` | What to render |
| Playbook | Active style playbook | Quality targets |
| Tools | `hyperframes_compose` (or `video_compose` HyperFrames mode), `sync-timings.py` | Rendering + timing correction |
| Media profiles | `lib/media_profiles.py` | Output format specs (resolution, codec, bitrate) |

## Process

### Step 1: Verify Assets

All narration, music, and image assets were generated in the asset stage. Before rendering:

1. **Verify narration exists:** Check `projects/<project>/assets/audio/narration.mp3` and per-section files exist
2. **Verify SRT subtitles exist:** Edge TTS generated `.srt` files alongside each narration section (via `--write-subtitles`). Check they all exist.
3. **Concatenate per-section SRTs** into a master subtitle file:
   ```bash
   # Adjust timestamps sequentially and merge
   python scripts/merge_srt.py projects/<project>/assets/narration/*.srt > projects/<project>/assets/subtitles/master.srt
   ```
4. **Verify background music:** Check `projects/<project>/assets/music/background_music.mp3` exists
5. **Verify all image/diagram assets** from the manifest exist on disk

6. **Probe durations:**
   ```bash
   ffprobe -v error -show_entries format=duration -of csv=p=0 projects/<project>/assets/audio/narration.mp3
   ffprobe -v error -show_entries format=duration -of csv=p=0 projects/<project>/assets/music/background_music.mp3
   ```
   - Narration ±15% of target video duration
   - Music ≥ video duration (will be looped if needed)

### Step 2: Determine Output Profile

Read the target platform from the brief artifact. Map to a media profile:

| Platform | Profile | Resolution | Notes |
|----------|---------|-----------|-------|
| **Mobile Portrait (locked)** | `tiktok` | **1080×1920 (9:16)** | All scenes rendered in portrait; reframing not needed |
| TikTok/Reels | `tiktok` | 1080×1920 | Vertical output |
| YouTube Shorts | `youtube_shorts` | 1080×1920 | Vertical output |

Get the exact encoding parameters via `ffmpeg_output_args(get_profile(name))`.

### Step 3: Build HyperFrames Composition (Simple Template Mode)

This pipeline renders through **HyperFrames** with a fixed template. No complex animations — just background image/video + sentence text. The only motion is:
- Background image crossfade between scenes (CSS transition)
- Sentence text fade-in/fade-out (GSAP opacity only, no transforms)

**DO NOT** add slide, scale, stagger, Ken Burns, count-up, chart animations, or any motion beyond simple opacity fades.

**Workflow:**

1. **Create a HyperFrames project** (one per video):
   ```bash
   npx hyperframes init projects/<project>/hyperframes --template blank
   ```

2. **Transform edit_decisions into index.html with fixed template structure:**

   Each cut is a `<section class="clip">` with two layers:
   - **Background layer**: full-viewport image or video filling the entire frame
   - **Text layer**: centered sentence(s) with simple fade transitions

   ```html
   <section class="clip" id="scene-1" data-start="0" data-duration="10"
            style="background: url('assets/images/scene-1-bg.jpg') center/cover no-repeat;">
     <div class="overlay"></div>
     <div class="text-container">
       <div class="sentence">交易的核心是风险管理，而不是预测市场。</div>
     </div>
   </section>
   ```

   **Background video alternative**: If a single full-duration background video was sourced (e.g., downloaded loop), use a `<video>` element instead of per-scene images:
   ```html
   <section class="clip" id="scene-1" data-start="0" data-duration="10">
     <video class="bg-video" src="assets/video/background.mp4" autoplay loop muted playsinline></video>
     <div class="overlay"></div>
     <div class="text-container">
       <div class="sentence">交易的核心是风险管理，而不是预测市场。</div>
     </div>
   </section>
   ```

3. **Scene type mapping (simplified — only two types):**
   | Type | Implementation |
   |---|---|
   | `background_image` | Per-scene `<section>` with `background: url(...) center/cover no-repeat`; crossfade between scenes via CSS |
   | `background_video` | Single `<video class="bg-video">` element behind all scenes; text overlays change per scene |

   No other scene types exist in this pipeline. All scenes follow the same layout template.

4. **Configure audio in index.html:**
   ```html
   <audio id="narration" src="assets/audio/narration.mp3" data-start="0" data-duration="60"></audio>
   <audio id="bgm" src="assets/music/background_music.mp3" data-start="0" data-duration="120" loop></audio>
   ```

5. **Add subtitle overlay:** Embed the Edge TTS SRT as an HTML caption layer, or use HyperFrames' built-in subtitle support. See `.agents/skills/hyperframes-media/SKILL.md` for caption authoring.

6. **Fixed template CSS (no GSAP needed for text transitions):**

   This pipeline uses ONE fixed layout — only the background and text content change between runs.

   ```css
   /* ── BASE: full-viewport background per scene ── */
   section.clip {
     position: relative;
     width: 1080px;
     height: 1920px;
     display: flex;
     align-items: center;
     justify-content: center;
     overflow: hidden;
   }

   /* ── Background video (fills entire viewport) ── */
   .bg-video {
     position: absolute;
     inset: 0;
     width: 100%;
     height: 100%;
     object-fit: cover;
     z-index: 0;
   }

   /* ── Dark overlay for text readability ── */
   .overlay {
     position: absolute;
     inset: 0;
     background: rgba(0, 0, 0, 0.35);
     z-index: 1;
   }

   /* ── Text container — centered, same position every scene ── */
   .text-container {
     position: relative;
     z-index: 2;
     max-width: 880px;
     padding: 40px 60px;
     text-align: center;
   }

   /* ── Individual sentence — simple fade via CSS opacity transition ── */
   .sentence {
     font-family: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
     font-size: 64px;
     font-weight: 400;
     line-height: 1.6;
     color: #FFFFFF;
     text-shadow: 0 2px 12px rgba(0, 0, 0, 0.6);
     opacity: 0;              /* hidden until its timer fires */
     transition: opacity 0.5s ease;
     position: absolute;      /* stack all sentences, show one at a time */
     left: 60px;
     right: 60px;
     top: 50%;
     transform: translateY(-50%);
   }
   .sentence.visible { opacity: 1; }

   /* ── Highlighted keywords ── */
   .sentence .highlight {
     color: #FFD93D;
     font-weight: 700;
   }

   /* ── Background crossfade between scenes ── */
   .clip { transition: opacity 0.8s ease; }
   ```

7. **Google Font Noto Sans SC:**

   Add to `<head>` before `<style>`:
   ```html
   <link rel="preconnect" href="https://fonts.googleapis.com">
   <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
   <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;700;900&display=swap" rel="stylesheet">
   ```

8. **Sentence timing script (replaces GSAP timeline):**

   Instead of GSAP timelines, use a simple timer-based script that toggles `.visible` class:

   ```javascript
   // Run when HyperFrames timeline reaches each scene
   const sentences = document.querySelectorAll('#scene-1 .sentence');
   let idx = 0;
   const showNext = () => {
     if (idx > 0) sentences[idx - 1].classList.remove('visible');
     if (idx < sentences.length) {
       sentences[idx].classList.add('visible');
       idx++;
       setTimeout(showNext, 3000); // per-sentence display duration from sync-timings
     }
   };
   showNext();
   ```

   **Important**: `sync-timings.py` (Step 5) will correct `data-start`/`data-duration` per scene AND per-sentence timing after ASR transcription. The initial estimate is a placeholder.

9. **Sentence text merging from script sections:**

   Determine sentence boundaries by splitting each scene's narration text on Chinese punctuation（。？！）:
   - One `.sentence` div per punctuation-delimited segment
   - Scene may have 1-4 sentences depending on narration pacing
   - If background video mode: sentences belonging to different original scenes still appear in sequence over the same video background

10. **Background image/video naming convention:**

    - Per-scene images: `scene-<id>-bg.jpg` in assets directory
    - Single video: `assets/video/background.mp4`
    - If a scene lacks a dedicated background image, use shared `bg-default.jpg`

### Step 4: Validate and Render

1. **Run validation:**
   ```bash
   npx hyperframes lint projects/<project>/hyperframes
   npx hyperframes validate projects/<project>/hyperframes
   ```
   Both must pass with zero errors before rendering. If validation fails, fix the issues and re-validate. Common issues: missing asset files, incorrect data-duration.

2. **Render:**
   ```bash
   npx hyperframes render projects/<project>/hyperframes --output projects/<project>/renders/output.mp4
   ```
   Or use `hyperframes_compose` / `video_compose` if a tool wrapper is available.

3. **Verify the render produced output:**
   ```bash
   ls -la projects/<project>/renders/output.mp4
   ffprobe -v quiet -print_format json -show_format -show_streams projects/<project>/renders/output.mp4
   ```
   - Video stream present
   - Audio stream present
   - Duration reasonable
### Step 5: Run sync-timings.py (Mandatory)

After the HyperFrames render, sync-timings.py corrects all scene timing using ASR transcription.

> **Critical — correct sync order**: The subtitle timing must be **derived from the actual narration audio**, not estimated from the script. The correct order:
> 1. Render the composition with placeholder timing (from script estimates)
> 2. **Run sync-timings.py** which transcribes the actual narration audio via `mlx_whisper`
> 3. Match transcript segments to scene text content
> 4. Patch `data-start` / `data-duration` / per-sentence timing to match real audio
> 5. **Re-render** with corrected timing
>
> This is why sync-timings.py runs AFTER the first render, not before. The real timing can only come from the audio that was actually generated.
>
> Common mistake: AI tries to calculate sentence display duration from character count or script timing. **Don't.** The ASR transcription tells you exactly when each word was spoken — use that.

**What it does:**
1. Transcribes the narration audio using `mlx_whisper` (Apple Silicon, word-level timestamps)
2. Parses each `<section class="clip">` in the HyperFrames `index.html`
3. Matches scene text content to ASR segments via fuzzy character-set Jaccard similarity
4. Computes corrected `data-start` and `data-duration` values
5. Patches `index.html` in-place with corrected timings

**Run it:**
```bash
python scripts/sync-timings.py projects/<project>/hyperframes
```

Or for a single project from the workspace root:
```bash
python scripts/sync-timings.py projects/<project_path>
```

**Command options:**
| Flag | Purpose |
|------|---------|
| `--dry-run` | Preview changes without modifying files |
| `--asr-json PATH` | Use pre-computed ASR JSON (skip re-transcription, for iteration) |
| `--narration PATH` | Custom narration path (default: `assets/audio/narration.mp3`) |
| `--html PATH` | Custom HTML path (default: `index.html`) |

**Expected output:**
- A timing correction report showing old → new start/duration values per scene
- Confidence score per scene (character-set Jaccard overlap with ASR)
- Low-confidence matches (< 30%) are flagged for manual review
- `index.html` is patched in-place with corrected `data-start` and `data-duration` values
- Audio element `data-duration` values are also corrected from ffprobe probe

**Quality gate — review the report:**
- Check for any scene with `< 30%` confidence — these need manual timing review
- Verify total duration shift is reasonable (large shifts indicate a matching failure)
- If critical scenes have low confidence, re-run with `--dry-run`, inspect, then manually correct

**Re-render if timings changed significantly:**
```bash
npx hyperframes render projects/<project>/hyperframes --output projects/<project>/renders/output.mp4
```

### Step 6: Post-Render Self-Review (Mandatory — ALL steps required)

After rendering, the agent **must review its own output** before presenting to the user. This catches issues the validator can't see (visual quality, audio sync, subtitle readability).

**CRITICAL: You MUST complete ALL of steps 6a through 6e. Do NOT skip any step.
The most common agent failure is doing 6a (frames) and 6c (visual) while skipping
6b (audio transcription) — which misses catastrophic issues like missing audio entirely.**

**6a. Probe rendered file (FIRST — gate for all other checks):**
```bash
ffprobe -v quiet -print_format json -show_format -show_streams rendered_video.mp4
```
Verify:
- Video stream exists (codec_type: "video") with correct resolution
- **Audio stream exists (codec_type: "audio")** — if NO audio stream, STOP and fix immediately
- Duration is within ±5% of target
- File size is reasonable (not 0 bytes)

**If audio stream is missing: the render did not embed audio. Do NOT proceed to present
the video to the user. Fix the audio configuration and re-render.**

**6b. Extract review frames:**
```python
from tools.analysis.frame_sampler import FrameSampler
midpoints = [(cut['in_seconds'] + cut['out_seconds']) / 2 for cut in cuts]
FrameSampler().execute({
    'input_path': 'path/to/rendered_video.mp4',
    'strategy': 'timestamps',
    'timestamps': midpoints,
    'output_dir': 'path/to/review-frames',
    'format': 'png',
})
```

**6c. Transcribe rendered audio (MANDATORY — do NOT skip):**
```python
from tools.analysis.transcriber import Transcriber
result = Transcriber().execute({
    'input_path': 'path/to/rendered_video.mp4',
    'model_size': 'base',
    'language': 'en',
    'output_dir': 'path/to/review-frames',
})
# If result returns 0 words: audio is silent/missing — STOP and fix
# If word count < 80% of script word count: audio is cut off — investigate
```

**6d. Visual inspection — review each frame:**
- Does the background (image or video) fill the entire viewport without stretching or letterboxing?
- Is the dark overlay applied? (text must be readable over bright/white backgrounds)
- Is the text centered and positioned correctly?
- Are highlighted keywords visibly different (color/weight)?
- Is text shadow present and strong enough for readability?
- Is the Google Font Noto Sans SC rendering (not falling back to system font)?
- Do sentences fade in/out smoothly (not cutting abruptly)?
- Is only ONE sentence visible at a time?
- Does the CTA/closing screen show correct text?

**6e. Audio inspection — check transcript against script:**
- Is the full narration captured? (compare last transcribed Chinese character to last scripted character)
- Any words cut off at the end? (narration exceeding video duration)
- Timing alignment — do narration segments roughly match their intended scenes? Check that sentence-by-sentence text transitions align with spoken pauses
- Is background music audible? (transcriber may not capture music, but ffprobe confirms audio stream)
- Are highlighted keywords spoken at the moment they appear on screen? (sync-timings output should confirm this)

**6f. Compile and present review to user:**

> **Post-render review for "[Video Title]":**
>
> **File:** [duration]s, [resolution], [file size] — audio stream: [present/MISSING]
> **Audio:** [Complete/Cut off at Xs] — [N]/[M] words transcribed from rendered output
> **Visuals:** [N scenes inspected] — [issues or "all scenes rendering correctly"]
> **Captions:** [Edge TTS SRT / HyperFrames HTML overlay / MISSING] — [synced correctly / needs review]
> **sync-timings:** [report summary — scenes corrected, total shift, low-confidence matches]
> **Issues found:** [list any issues with severity]
>
> **Recommendations:** [what to fix, if anything]
>
> Want me to fix these issues and re-render, or is this good to go?

**Only after user approves (or agent finds zero issues) should the video be considered final.**

### Step 6-old: File and Content Verification

**File verification:**
- [ ] Output file exists at declared path
- [ ] File size is reasonable (not 0 bytes, not suspiciously small)
- [ ] File is a valid container (ffprobe succeeds)

**Content verification:**
- [ ] Duration within ±5% of target
- [ ] Resolution matches selected profile
- [ ] Audio channels present (stereo)
- [ ] No audio clipping or silence gaps > 1s

**Quality check (covered by self-review above):**
- [ ] Visual: all scene frames inspected
- [ ] Audio: full transcription verified
- [ ] Subtitles: visible and correctly timed

### Step 7: Build Render Report

```json
{
  "version": "1.0",
  "outputs": [
    {
      "path": "renders/output.mp4",
      "format": "mp4",
      "codec": "h264",
      "resolution": "1080x1920",
      "fps": 30,
      "duration_seconds": 62.4,
      "file_size_mb": 45.2,
      "audio_codec": "aac",
      "audio_channels": 2,
      "render_strategy": "hyperframes",
      "render_time_seconds": 180
    }
  ],
  "render_summary": {
    "total_cuts_rendered": 12,
    "subtitles_burned": true,
    "audio_tracks_mixed": 3,
    "target_duration_seconds": 60,
    "actual_duration_seconds": 62.4
  }
}
```

### Step 8: Self-Evaluate

Score (1-5):

| Criterion | Question |
|-----------|----------|
| **Playability** | Does the video play without errors in a standard player? |
| **Duration accuracy** | Is actual duration within ±5% of target? |
| **Audio quality** | Is narration clear, music balanced, no clipping? |
| **Visual quality** | Are images sharp, transitions smooth, no artifacts? |
| **Subtitle accuracy** | Are subtitles present, readable, and synced? |

If any dimension scores below 3, investigate and re-render.

### Step 9: Submit

Validate the render_report against the schema and persist via checkpoint.

## Common Pitfalls

- **Missing asset files**: Always verify every referenced file exists before starting the render. A missing file mid-render wastes time.
- **Adding animations (blocked)**: Do NOT add GSAP animations beyond simple opacity fades. No slide, scale, stagger, Ken Burns, count-up — this pipeline uses simple template mode by design.
- **Audio sync drift**: Accumulated timing errors across narration segments cause audio-visual desync. sync-timings.py corrects this, but if ASR confidence is low for key scenes, manual verification is needed.
- **sync-timings.py low confidence**: If character overlap between scene text and ASR segments is below 30%, the timing correction may be wrong. Check the report and manually adjust if needed.
- **Subtitle encoding**: Burn subtitles into the video (hardcoded) for maximum compatibility. Don't rely on soft subtitles for social media.
- **Chinese font rendering**: Ensure the HyperFrames composition loads Google Font Noto Sans SC via `<link>` in `<head>`. Verify the font is being used and not falling back to system fonts.
- **Background image vs text contrast**: Natural scenery backgrounds vary in brightness. The dark overlay (`rgba(0,0,0,0.35)`) is required for text readability. If background images are unusually bright/dark, adjust overlay opacity accordingly.
- **Sentence timing (not stagger)**: Each `.sentence` should stay visible long enough to be comfortably read. Default ~2-3s per short sentence, 4-5s for long ones. sync-timings.py will correct from ASR.
- **Google Fonts offline fallback**: If the render environment has no internet, Noto Sans SC may not load. Add `'PingFang SC', 'Microsoft YaHei', sans-serif` as fallback stack.
- **mlx_whisper not installed**: sync-timings.py requires `mlx-whisper` (Apple Silicon only). On non-Apple-Silicon machines, pass `--asr-json` with pre-computed Whisper output.
- **HyperFrames lint failures**: `npx hyperframes lint` catches structural issues (missing data-attributes, broken asset references). Fix all lint errors before re-rendering — don't defer to post-render review.
- **Background video audio**: If using a background video with audio track, mute it (`muted` attribute) — narration and music are the audio layers.
