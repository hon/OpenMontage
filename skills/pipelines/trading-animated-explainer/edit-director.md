# Edit Director — Trading Explainer Pipeline

## Customizations from base `animated-explainer/edit-director.md`

This file is forked from `skills/pipelines/animated-explainer/edit-director.md`.
Changes made for the `trading-animated-explainer` pipeline:
- **Runtime locked to HyperFrames** — all scene types render via HTML/CSS/GSAP, not Remotion components
- **TTS locked to Edge TTS (zh-CN-YunyangNeural)** — subtitle timing uses Edge TTS word-level timestamps
- **Post-compose sync-timings.py** — final timing correction happens after render, not in this stage
- **Zero cost** — all assets are free; no paid APIs used
- **Portrait 9:16 (mobile竖屏)** — all cuts and compositions assume 1080×1920 portrait; no landscape reframing needed
- **Simple template mode (no animations)** — cuts define background source + text timing only; no Ken Burns, no complex transforms

## When to Use

You are the Editor for a generated trading explainer video. You have an `asset_manifest` with all generated files, a `scene_plan` with visual structure, and a `script` with timing. Your job is to assemble the edit decision list (EDL): what plays when, how elements layer, where subtitles go, and how music and narration interact.

This is where raw assets become a coherent video. Good editing makes average assets shine; bad editing wastes great assets.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/edit_decisions.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["assets"]["asset_manifest"]`, `state.artifacts["scene_plan"]["scene_plan"]`, `state.artifacts["script"]["script"]` | Assets, visual plan, timing |
| Playbook | Active style playbook | Transitions, pacing rules, overlay styles |

## Process

### Step 1: Map Assets to Timeline

For each scene in the scene plan:
1. Find the matching assets from the asset manifest (by `scene_id`)
2. Find the matching narration audio (by script section)
3. Note the scene's timing (`start_seconds`, `end_seconds`)

Build a timeline map from the script sections (simple — one background image per section):
```
section-1 → cut-1: bg-scene-1.jpg | narration: "市场是概率的游戏..."
section-2 → cut-2: bg-scene-2.jpg | narration: "很多人因为挫败感而离开..."
...
```

**Simple template mapping (this pipeline uses only two scene types):**
- `background_image` → One background image per cut. No Ken Burns, no zoom — just a static full-viewport background.
- `background_video` → A single video asset (downloaded stock video) serving as background for all cuts. Text overlays change per cut.
- All cuts use the same fade transition (`fade`, 0.4s) — do NOT vary transitions.
- Subtitles are generated from Edge TTS timestamps and embedded as SRT or HTML overlays during compose.

### Step 2: Define Cuts (Simplified)

Each cut defines the background image and timing. No transforms or complex animations:

```json
{
  "id": "cut-1",
  "scene_id": "scene-1",
  "source": "bg-scene-1",
  "in_seconds": 0,
  "out_seconds": 10,
  "transition_in": "fade",
  "transition_out": "fade",
  "transition_duration": 0.4
}
```

**Layering (simplified — one layer only):**
- Each cut is a full-viewport background image. Text and subtitles are overlaid by the compose stage, not defined in the cut.
- No Ken Burns, no zoom, no scale animation — the image fills the viewport at 100% scale, centered.
- All cuts use the same `fade` transition. Do NOT vary transition types.

### Step 3: Configure Subtitles (Sentence-by-Sentence)

Subtitles display **one sentence at a time** in the center of the screen, synchronized with narration:

```json
{
  "subtitles": {
    "enabled": true,
    "style": "sentence-by-sentence",
    "font": "Noto Sans SC",
    "font_size": 64,
    "color": "#FFFFFF",
    "text_shadow": "0 2px 12px rgba(0,0,0,0.6)",
    "position": "center",
    "animation": "fade-in-out",
    "highlight_color": "#FFD93D"
  }
}
```

**Subtitle behavior:**
- One sentence visible at a time, centered vertically
- Sentence fades in when narrator starts speaking it, fades out when it ends
- Simple CSS opacity transition (0.5s ease) — no slide, no scale, no stagger
- Highlight key terms in `#FFD93D` (warm gold) — max 1-3 highlighted words per sentence

**Timing source**: Edge TTS `--write-subtitles` SRT output provides word-level timestamps. The compose stage merges SRT and runs `sync-timings.py` for ASR-based correction.

### Step 4: Configure Audio Layers

```json
{
  "audio": {
    "narration": {
      "segments": [
        { "asset_id": "narration-s1", "start_seconds": 0 },
        { "asset_id": "narration-s2", "start_seconds": 10 }
      ]
    },
    "music": {
      "asset_id": "music-bg",
      "volume": 0.08,
      "fade_in_seconds": 2,
      "fade_out_seconds": 3,
      "ducking": {
        "enabled": true,
        "threshold_db": -3,
        "reduction_db": -8,
        "attack_ms": 200,
        "release_ms": 500
      }
    },
    "sfx": []
  }
}
```

**Music ducking**: Music volume drops when narration plays, rises during pauses. Use playbook's `audio.ducking_threshold_db`.

### Step 5: Apply Pacing Rules

Simple rules for this pipeline:
- Each cut duration matches its script section duration
- All cuts use `fade` transition with 0.4s duration
- No cut should be shorter than 2s

### Step 6: Verify Edit Completeness

**Timeline coverage:**
- [ ] Cuts span full video duration (no black frames)
- [ ] Every scene in scene_plan has exactly one cut
- [ ] No gaps between cuts

**Asset references:**
- [ ] Every cut's `source` references a valid asset_id from the manifest
- [ ] Every narration segment references a valid audio asset
- [ ] Music asset exists (or `"music_status": "unavailable"` is noted)

**Audio sync:**
- [ ] Narration segments are ordered and non-overlapping
- [ ] Narration timing aligns with corresponding visual cuts

**Subtitles:**
- [ ] Subtitles set to `sentence-by-sentence` style
- [ ] One sentence visible at a time in center of screen

### Step 7: Self-Evaluate

Score (1-5):

| Criterion | Question |
|-----------|----------|
| **Continuity** | Does every second of the video have a background visual? |
| **Audio-visual sync** | Does what you see match what you hear at every moment? |
| **Subtitle quality** | Are sentences readable, synced, and properly faded? |
| **Simplicity** | Are all cuts simple fades with no extra animations? |

If any dimension scores below 3, revise.

### Step 8: Submit

Validate the edit_decisions artifact against the schema and persist via checkpoint.

## Common Pitfalls

- **Adding animations**: This pipeline uses simple template mode. Do NOT add Ken Burns, zoom, slide, count-up, or any animation beyond basic fade.
- **Forgetting gaps**: If scene-1 ends at 10s and scene-2 starts at 10.5s, there's a 0.5s black frame. Check for gaps.
- **Audio drift**: Narration audio may be slightly longer/shorter than planned. Adjust visual cuts to match actual narration durations.
- **No ducking**: Music playing at full volume under narration makes the video unwatchable. Always configure ducking.
- **Multiple sentences on screen**: Only ONE sentence visible at a time. The compose stage handles sentence rotation via timer.
- **Subtitle font mismatch**: Use Noto Sans SC for Chinese text, not a default serif or sans-serif.
