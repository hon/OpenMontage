# Edit Director — Explainer Templates Pipeline

## When to Use

You are the Edit Director for an explainer video. You have a `scene_plan` with per-scene background assignments and an `asset_manifest` with all generated files. Your job is to produce an `edit_decisions` artifact — the timeline that the compose stage will render.

This pipeline uses a **simple template structure**: each scene is a full-viewport background with centered text. The EDL is straightforward: one cut per scene, sequential.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/edit_decisions.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["scene_plan"]["scene_plan"]`, `state.artifacts["assets"]["asset_manifest"]` | What to cut |
| Template config | `template.yaml` | Composition structure |

## Process

### Step 1: Build Timeline

Map each scene from the scene_plan to a cut in the edit timeline:

```
section-1 → cut-1: bg-scene-1.jpg | narration-s1.mp3 | text: "市场是概率的游戏..."
section-2 → cut-2: bg-scene-2.jpg | narration-s2.mp3 | text: "很多人因为挫败感而离开..."
```

Each cut has:
- **Background**: Image or video asset from the manifest
- **Narration**: Per-section narration audio
- **Text**: Sentence(s) from the script section, displayed one at a time
- **Duration**: From script timing (will be corrected by sync-timings.py)

### Step 2: Build edit_decisions

```json
{
  "timeline": [
    {
      "cut_id": "c1",
      "scene_id": "s1",
      "type": "background_image",
      "in_seconds": 0,
      "out_seconds": 15,
      "assets": {
        "background": "assets/images/scene-s1-bg.jpg",
        "narration": "assets/audio/narration.mp3"
      },
      "sentences": [
        {
          "text": "市场是概率的游戏，充满了不确定性。",
          "start_offset": 0,
          "duration_seconds": 5,
          "highlight_words": ["概率"]
        },
        {
          "text": "很多时候你做了所有正确的事情，但市场依然给你一张亏损的单子。",
          "start_offset": 5,
          "duration_seconds": 10,
          "highlight_words": ["亏损"]
        }
      ]
    }
  ],
  "template": "minimal",
  "render_runtime": "hyperframes"
}
```

### Step 3: Self-Review

- [ ] All cuts reference valid asset paths from the manifest
- [ ] Timeline covers the full video duration with no gaps
- [ ] Per-sentence timing is proportional (short sentence = shorter duration)
- [ ] `render_runtime` matches the template's `composition.runtime`

### Step 4: Submit

Validate the edit_decisions against the schema and persist via checkpoint.
