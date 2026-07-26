# Asset Director — Trading Explainer Pipeline

## Customizations from base `animated-explainer/asset-director.md`

This file is forked from `skills/pipelines/animated-explainer/asset-director.md`.
Changes made for the `trading-animated-explainer` pipeline:
- **TTS locked to Edge TTS (zh-CN-YunyangNeural)** — `tts_selector` replaced with explicit Edge TTS CLI
- **Runtime locked to HyperFrames** — no Remotion components; all scenes rendered via HTML/CSS/GSAP
- **Subtitles generated via edge-tts --write-subtitles** — SRT with word-level timing, fed into HyperFrames
- **Zero cost enforced** — all assets must be free; no paid AI generation (FLUX, GPT Image, ElevenLabs, etc.)
- **Portrait 9:16 (mobile竖屏)** — all background images sourced as portrait (1080×1920 minimum); search orientation locked to `portrait`

## Zero Cost Enforcement

This pipeline has a **$0.00 budget**. No paid API calls are allowed:

| Asset Type | Allowed Providers | Reason |
|---|---|---|
| Narration | Edge TTS (`zh-CN-YunyangNeural`) | Free, local CLI |
| Background images | Stock photo APIs (Pexels, Unsplash, Pixabay) or local generation | Free/API-key-free image sources |
| Diagrams | `diagram_gen` (Mermaid) | Free, local |
| Code snippets | `code_snippet` | Free, local |
| Music | Pixabay stock music search, or `music_library/` folder | Free stock, no paid generation |
| Enhancement/transcription | Local tools only (ffmpeg, ffprobe) | Free |
| Composition/render | HyperFrames (`npx hyperframes`) | Free, local Node.js |

**If a free provider is unavailable (e.g. stock API rate-limited):** skip that asset type or use a local fallback. Do NOT default to a paid provider. Surface the limitation clearly in the asset manifest.

## When to Use

You are the Asset Producer for a generated trading explainer video. You have a `scene_plan` with required assets and a `script` with narration text. Your job is to generate every asset needed: narration audio, images, diagrams, code snippets, and background music. Every file must exist on disk before you finish.

This is where plans become real files. A missing or low-quality asset will torpedo the final video.

## Animation authoring — HyperFrames-only

This pipeline is locked to HyperFrames (HTML/CSS/GSAP). All animated scenes render through HyperFrames, not Remotion.

For scene animation patterns read:
- `.agents/skills/hyperframes-animation/SKILL.md` — animation blueprints, GSAP timelines, scene transitions
- `.agents/skills/gsap-timeline/SKILL.md` — GSAP timeline sequencing for multi-tween choreography
- `.agents/skills/gsap-plugins/SKILL.md` — GSAP plugins (SplitText, DrawSVG) for kinetic typography and line reveals

**Data charts (bar/line/pie/KPI):** Use HyperFrames registry chart components via `hyperframes add chart` or author CSS/SVG-based chart sections. Do NOT use Remotion chart components — they are not available in this pipeline.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/asset_manifest.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["scene_plan"]["scene_plan"]`, `state.artifacts["script"]["script"]`, `state.artifacts["proposal"]["proposal_packet"]` | What to produce |
| Playbook | Active style playbook | Image prompts, diagram style, audio preferences |
| Tools | `edge-tts` (CLI), `image_selector`, `video_selector`, `diagram_gen`, `code_snippet`, `music_gen` | Generation capabilities |
| Cost tracker | `tools/cost_tracker.py` | Budget governance |

## Process

### Step 1: Inventory Required Assets

Walk every scene in the scene plan. For each `required_assets` entry, create an asset task:

```
Asset Task:
  scene_id: scene-3
  type: diagram
  description: "Mermaid flowchart: query -> encode -> search -> rank -> return"
  source: generate
  tool: diagram_gen
  estimated_cost: $0.00
```

Also create tasks for:
- **Narration audio** — one per script section (use Edge TTS `zh-CN-YunyangNeural`)
- **Background music** — one track for the whole video (use `music_gen` or select from library)
- **Sound effects** — per playbook's `sfx_style` (optional, use `music_gen` or stock)

### Step 2: Check Budget (Zero-Cost Pipeline)

This pipeline has a **$0.00 budget**. No tool or API call may incur a cost:

1. Verify every asset task uses a free provider (stock photo, local tool, etc.)
2. If a required asset type has no free provider available, surface it as a blocker — do not silently skip or downgrade
3. The cost tracker should report `$0.00` total for all assets; if any line item shows a cost > $0, find a free alternative or skip that asset
4. No approval gate needed for $0 cost — proceed directly to generation

### Step 2b: Sample Preview (Prevents Wasted Spend)

Before batch-generating assets, produce one sample of each expensive asset type and present them to the user for approval:

1. **TTS sample**: Generate narration for `script.voice_performance.sample_section_id` when present; otherwise pick the section with the most demanding delivery using Edge TTS (`zh-CN-YunyangNeural`). Play it for the user. Confirm voice, pace, pauses, emphasis, and tone are acceptable before generating the rest. Edge TTS is free — samples cost nothing.
2. **Image sample**: Generate one image for the most representative scene. Show it to the user. Confirm the style, quality, and prompt approach before batch-generating all images.
3. **Music sample** (if using `music_gen`): Generate one short clip. Confirm mood and energy before committing.

If the user rejects a sample:
- Adjust the parameters (voice, prompt style, provider) and regenerate the sample.
- Do not batch-generate until the sample is approved.
- Max 3 sample iterations per asset type before escalating to the user for a decision.

This step typically costs $0.03–0.08 total and prevents $1–3 of wasted generation.

### Step 3: Generate Narration (Edge TTS — zh-CN-YunyangNeural)

This pipeline uses **Edge TTS** with **`zh-CN-YunyangNeural`** (Chinese male voice) as the sole TTS provider. Edge TTS is free, offline-capable, and provides SRT subtitle output via `--write-subtitles`.

**Prerequisite check:** Before generating, verify `edge-tts` is installed:
```bash
pip install edge-tts
edge-tts --list-voices | grep YunyangNeural
# Expected: Name: zh-CN-YunyangNeural
```

**Per-section generation:**

For each script section:
1. Extract the narration text (Chinese)
2. Read `script.voice_performance` and section `delivery_cues`
3. Apply speaker directions via Edge TTS parameters:
   - `--rate` — speaking rate adjustment (`+0%` default, `-20%` for slow/emphatic, `+20%` for energetic)
   - `--pitch` — pitch adjustment (`+0Hz` default, `-10Hz` for deeper, `+10Hz` for brighter)
   - `--volume` — volume level (`+0%` default)
4. Generate with subtitle export:
   ```bash
   edge-tts \
     --voice zh-CN-YunyangNeural \
     --text "<section text>" \
     --rate <rate_adjustment> \
     --pitch <pitch_adjustment> \
     --write-media "projects/<project>/assets/narration/s<section_num>.mp3" \
     --write-subtitles "projects/<project>/assets/narration/s<section_num>.srt"
   ```
5. The `--write-subtitles` flag produces SRT with word-level timing — this feeds into the compose stage for HyperFrames subtitle overlay
6. Verify the audio file exists and duration matches expected timing (±15%)
7. Record the applied `voice_performance` metadata on each narration asset

**Edge TTS parameter cheat-sheet:**
| Parameter | Range | Effect |
|-----------|-------|--------|
| `--rate` | `-50%` to `+50%` | Speaking speed. Default `+0%`. Use `-10%` to `-20%` for instructional/emphatic delivery. |
| `--pitch` | `-50Hz` to `+50Hz` | Voice pitch. Default `+0Hz`. Use `-15Hz` to `-30Hz` for deeper/authoritative. |
| `--volume` | `-50%` to `+50%` | Audio gain. Default `+0%`. |

**Pronunciation guide:** Edge TTS handles Chinese well by default. For technical terms (English acronyms, trading jargon), ensure they are embedded with natural Chinese prosody. If Edge TTS mispronounces a term, add a SSML phoneme tag:
```xml
<phoneme alphabet="sapi" ph="jiā yì">交易</phoneme>
```
Use this only as a last resort — Edge TTS Chinese models are generally accurate.

**Flat voice failure:** If the generated voice sounds monotone, robotic, rushed,
or ignores intended pauses, do not batch the remaining sections. Adjust `--rate`
and `--pitch` parameters, add punctuation-based pauses in the text, and regenerate the sample.

**Full narration concat:** After all sections are generated, concatenate them into a single file for HyperFrames:
```bash
ffmpeg -f concat -safe 0 -i <(for f in projects/<project>/assets/narration/s*.mp3; do echo "file '$PWD/$f'"; done) \
  -c copy "projects/<project>/assets/audio/narration.mp3"
```
Concatenate SRT files similarly for a master subtitle track. The compose stage runs `sync-timings.py` to fine-correct all timings against ASR transcription.

### Step 4: Generate Visual Assets

Process asset tasks grouped by tool for efficiency:

**Background images — natural scenery (free stock photo APIs)**:

Every scene needs a full-HD natural scenery background. Source one per scene (`scene-<id>-bg.jpg`), plus one fallback (`bg-default.jpg`).

Use **free stock photo APIs** — do NOT use paid AI image generation (FLUX, GPT Image, etc.). Prefer `pexels_search`, `unsplash_search`, or `pixabay_search` tools if available, or download directly via web_search + webfetch.

**Search formula — natural scenery photos:**

Search for real photographs matching the scene's emotional tone:

| Scene Mood | Example Search Query |
|---|---|
| Calm/educational | "misty mountain lake sunrise high resolution landscape" |
| Urgent/exciting | "storm clouds ocean dramatic sky landscape photograph" |
| Hopeful/inspiring | "sunlight through forest golden hour nature photograph" |
| Serious/weighty | "deep canyon twilight dramatic rock formation landscape" |
| Neutral/general | "lush green hills morning light rolling landscape" |

**Search parameters:**
```
query: <search terms>
min_width: 1080
min_height: 1920
orientation: portrait
```

**Download to correct path:** `projects/<project>/assets/images/scene-<scene_id>-bg.jpg`

**Stock photo API key note:** Pexels, Unsplash, and Pixabay all offer free API keys. If none are configured, fall back to web_search for free-license landscape photos on sites like Wikimedia Commons or Pexels direct download.

**Rules:**
- Always 1080×1920 portrait minimum (9:16) — the HyperFrames composition treats background images as full-viewport cover
- No text, no people, no urban elements — these are pure nature backgrounds
- Vary the scenery type between scenes (no back-to-back identical biomes)
- Source all backgrounds first, then any content-specific assets
- If multiple scenes, vary the biome (mountain ↔ ocean ↔ forest ↔ canyon ↔ lake)

**Output naming:** `projects/<project>/assets/images/scene-<scene_id>-bg.jpg`

**Fallback:** If a scene somehow lacks a dedicated background, `projects/<project>/assets/images/bg-default.jpg` is used.

**Background video alternative (one full-duration video instead of per-scene images):**

If a suitable free stock video is found (e.g., Pixabay video, Pexels video — nature scene, slow motion, loopable), download a single video to serve as background for the entire video:

1. Search for portrait/vertical stock video (9:16, 1080×1920 or higher):
   ```
   query: <nature scene matching video mood>
   orientation: portrait
   min_duration: <total video duration>
   ```
2. If no single video covers the full duration, download the longest available and it will loop during render
3. Download to: `projects/<project>/assets/video/background.mp4`
4. Verify with ffprobe (resolution, duration, codec)
5. If video background is used, set `background_type: "video"` in the asset manifest instead of per-scene images
6. **Note**: Mute the video's audio track if it has one — narration and music are the audio layers

**If no portrait stock video is available:** fall back to per-scene background images (the default). Do not use landscape video cropped to portrait.

(Beyond backgrounds, this pipeline does NOT generate content-specific images, diagrams, charts, or illustrations. All scenes use the same text-over-background template.)

**Diagrams (`diagram_gen`)**:
1. Convert the scene description into valid Mermaid syntax
2. Apply playbook's `asset_generation.diagram_style`
3. Generate SVG/PNG
4. Verify all nodes and edges are present

**Code snippets (`code_snippet`)**:
1. Extract language and code from the scene description
2. Apply syntax highlighting theme from playbook's overlay styles
3. Generate highlighted image or HyperFrames-compatible inline SVG

### Step 5: Generate Music (Free Stock Only)

This pipeline has a $0 budget — no paid music generation.

1. Read playbook's `audio.music_mood` and `audio.music_volume`
2. Check the music decision from `proposal_packet.production_plan.music_source` (set by the Proposal Director)
3. Source the background track in this priority order (all free):
   - **User music library (`music_library/`)**: If the folder exists and has tracks, pick the best match for the playbook's `audio.music_mood`. Copy to `projects/<project>/assets/music/background_music.mp3`.
   - **Pixabay stock music search**: Search via `pixabay_search(query=<mood+genre>, music=true)` or web search for royalty-free music. Download the best match.
   - **No music available**: If no free source is found, set `"music_status": "unavailable"` in the asset manifest. The video proceeds without background music — this is acceptable for zero-cost production. Report it clearly.
4. Duration should be at least as long as total video duration. If shorter, it can be looped by the compose stage.
5. Verify the audio file exists at `projects/<project>/assets/music/background_music.mp3`

**Critical:** Do NOT use `music_gen` (ElevenLabs) or `suno_music` — they are paid APIs. If no free music is found, proceed without music rather than failing the budget.

### Step 6: Build Asset Manifest

Assemble all generated assets into the manifest:

```json
{
  "version": "1.0",
  "assets": [
    {
      "id": "narration-s1",
      "type": "audio",
      "subtype": "narration",
      "path": "assets/narration/s1.mp3",
      "source_tool": "edge_tts",
      "scene_id": "scene-1",
      "duration_seconds": 8.2,
      "cost_usd": 0.00
    },
    {
      "id": "bg-scene-1",
      "type": "image",
      "subtype": "background",
      "path": "assets/images/scene-1-bg.jpg",
      "source_tool": "pexels_search",
      "scene_id": "scene-1",
      "cost_usd": 0.00,
      "source_url": "https://www.pexels.com/photo/..."
    },
    {
      "id": "bg-scene-2",
      "type": "image",
      "subtype": "background",
      "path": "assets/images/scene-2-bg.jpg",
      "source_tool": "pexels_search",
      "scene_id": "scene-2",
      "cost_usd": 0.00,
      "source_url": "https://www.pexels.com/photo/..."
    },
    {
      "id": "bg-scene-3",
      "type": "image",
      "subtype": "background",
      "path": "assets/images/scene-3-bg.jpg",
      "source_tool": "pexels_search",
      "scene_id": "scene-3",
      "cost_usd": 0.00,
      "source_url": "https://www.pexels.com/photo/..."
    },
    {
      "id": "music-bg",
      "type": "audio",
      "subtype": "music",
      "path": "assets/music/background.mp3",
      "source_tool": "pixabay_music",
      "duration_seconds": 62,
      "cost_usd": 0.00
    }
  ],
  "total_cost_usd": 0.00,
  "generation_summary": {
    "narration_sections": 5,
    "background_images": 3,
    "music_tracks": 1
  }
}
```

### Pre/Post Self-Review for Background Image Selection

For stock photo search queries, use simple search terms that describe the scene directly. No AI prompt engineering needed — stock APIs search by keywords, not captions. Just ensure:
- Query contains scenery type + mood + "portrait": e.g., `"misty mountain lake sunrise portrait"`
- The result image width ≥ height (portrait orientation)

### Step 7: Verify All Assets

**Existence check:**
- [ ] Every asset `path` exists on disk
- [ ] Every narration section has a corresponding audio file
- [ ] Every scene has a background image (`scene-<id>-bg.jpg`)
- [ ] Fallback `bg-default.jpg` exists (for scenes without dedicated background)
- [ ] Background music file exists (or `"music_status": "unavailable"` recorded)

**Quality check:**
- [ ] Narration durations within ±15% of expected timing
- [ ] Narration assets record `voice_performance.delivery_cues_applied`
- [ ] All narration generated with Edge TTS (`zh-CN-YunyangNeural`) — verify voice ID consistency
- [ ] Each section has a matching `.srt` subtitle file from `--write-subtitles`
- [ ] Approved TTS sample uses the same --rate/--pitch parameters as the batch
- [ ] Edge TTS SSML phoneme overrides applied for mispronounced technical terms (if needed)
- [ ] Background images are 1080×1920 portrait (9:16), no text/people/urban elements
- [ ] Background images vary in biome/scenery type between adjacent scenes
- [ ] If video background used: file is portrait 1080×1920, audio is muted in render
- [ ] Total cost is $0.00 — verify no paid API calls were made

### Step 8: Self-Evaluate

Score (1-5):

| Criterion | Question |
|-----------|----------|
| **Completeness** | Does every scene have a background image (or is video background ready)? |
| **Audio quality** | Does Edge TTS narration sound natural with correct pace/rate/pitch? |
| **Background quality** | Are backgrounds portrait 1080×1920, no text/people/urban, varied biomes? |
| **Budget adherence** | Is total cost $0.00? No paid APIs used? |

If any dimension scores below 3, fix before proceeding.

### Step 9: Submit

Validate the asset_manifest against the schema and persist via checkpoint.

## Common Pitfalls

- **Background images with people or text**: Choose stock photos without people, text, or buildings — they distract from narration.
- **Ignoring narration timing**: If TTS produces 12s of audio for a 10s section, the edit phase will struggle. Check durations.
- **Missing pronunciation guide**: Technical terms will be mispronounced without explicit guidance. Add Edge TTS SSML if needed.
- **Inconsistent background orientation**: All background images MUST be portrait 1080×1920. Do not mix orientations.
- **Background video with audio**: If using a video background, note in manifest that audio must be muted during compose.
- **No music fallback**: If no free stock music is found, record `"music_status": "unavailable"` and proceed without music.
- **Adding complexity**: This pipeline does NOT use diagrams, charts, or AI-generated images. Stock photos only.

Do not rely on stale knowledge. When in doubt, search first.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true` in the pipeline YAML). After review passes:
checkpoint with `status="awaiting_human"`, present the summary, and **END YOUR TURN**.
Do not start the next stage in the same response. Approval is per-gate — an earlier "go ahead" does not cover this gate.
