# Scene Director — Explainer Templates Pipeline

## When to Use

You are the Scene Planner for an explainer video. You have a `script` artifact with timestamped sections from the user's confirmed copy. Your job is to map each script section to visual scenes using only the scene types allowed by the active template.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/scene_plan.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["script"]["script"]` | Script sections |
| Template config | `template.yaml` of selected template | Allowed scene types, viewport |
| Playbook | Active style playbook | Visual language |

## Process

### Step 0: Read Template Config

Before planning any scenes, read the active template definition:
- Path: `config.templates[brief.template].file` (e.g., `templates/minimal/template.yaml`)
- Key field: `scene_types.allowed` —**only these scene types may be used**

This pipeline's scene-director supports a growing vocabulary of scene types. The template defines which subset is available.

### Step 1: Analyze the Script

Read every section. For each, note:
- What concept is being explained?
- What is the emotional beat? (calm/educational, serious/weighty, hopeful/inspiring, neutral/general)
- How much time is available? (end_seconds - start_seconds)

### Step 1.5: Derive Scene Timing Windows from Narration Cues

Scene `start_seconds`/`end_seconds` are NOT arbitrary. They are derived from the
script section's narration cue timestamps (read from `state.artifacts["script"]["script"]`).

Read the `timing` config from the active template's `template.yaml`:
- `timing.lead_in_seconds` (default 0.3) — scene start = first cue start − lead_in
- `timing.tail_seconds` (default 0.3) — non-last scene: duration = cue span + tail
- `timing.last_tail_seconds` (default 0.8) — last scene: duration = cue span + last_tail

**Rules:**
- **Scene start** = first narration cue start in that section − `lead_in_seconds`. Clamp to 0 for scene 1.
- **Non-last scene duration** = (last cue end − first cue start) + `tail_seconds`
- **Last scene duration** = (last cue end − first cue start) + `last_tail_seconds` (room for the outro fade)
- Measured narration gaps are 0.10–0.16s — do not stretch scene windows to fill them; the lead/tail padding is sufficient.
- **Never use round numbers** (10s, 8s) — use the cue-derived values, or the audio will drift out of sync with the visuals.

The script artifact already carries per-section `start_seconds`/`end_seconds` from the script-director's cue-timed formatting. Use those as the starting point, then apply the lead-in/tail padding from `template.yaml`.

These windows become `start_seconds`/`duration_seconds` on each scene in the scene_plan, which the compose-director translates into `data-start`/`data-duration` on the HTML sections.

### Step 2: Define Background for Each Section

Each script section maps to **exactly one scene**. Choose a visual mood that matches the emotional beat:

| Script Mood | Recommended Scenery | Stock Search Hint |
|---|---|---|
| Calm / Educational | Misty mountains, calm lake, forest clearing, sunrise meadow | `"misty mountain lake sunrise landscape"` |
| Serious / Weighty | Storm clouds, mountain peak, deep canyon, dark ocean | `"dramatic canyon twilight landscape"` |
| Hopeful / Inspiring | Sunrise, open field, mountain vista, bird in flight | `"golden hour forest sunlight warm"` |
| Neutral / General | City skyline, river, library, open sky | `"lush rolling hills morning light landscape"` |

**Constraint:** Only use scene types from the template's `scene_types.allowed` list. For example, if the template only allows `background_image`, every scene must be type `background_image`.

### Step 3: Generate Scene Plan

Output machine-readable scene_plan:

```json
{
  "scenes": [
    {
      "id": "s1",
      "type": "background_image",
      "script_section_id": "s1",
      "start_seconds": 0,
      "end_seconds": 15,
      "duration_seconds": 15,
      "background": {
        "type": "image",
        "source": "stock_photo",
        "search_query": "misty mountain lake sunrise wide shot",
        "mood": "calm reflective"
      },
      "text_overlays": [
        {
          "text": "市场是概率的游戏，充满了不确定性。",
          "highlight_words": ["概率"]
        }
      ]
    }
  ]
}
```

**Scene type variations (when allowed by template):**

- `background_image`: Full-viewport static image. Only `search_query` and `source` needed. Portrait 1080×1920.
- `background_video`: Full-viewport looping video. Same structure but `type: "video"` under `background`.

### Step 4: Self-Review

**Coverage check:**
- [ ] Scenes span the full script duration (first scene starts at 0s, last scene ends at total_duration)
- [ ] Every script section has exactly one corresponding scene
- [ ] No gaps > 1s between scenes

**Template compliance:**
- [ ] Every scene type is in the template's `scene_types.allowed` list
- [ ] Scene types default to the template's `scene_types.default` when no strong reason to differ

**Background consistency:**
- [ ] No two consecutive scenes use the same biome (vary mountain/ocean/forest/canyon/lake)
- [ ] Each scene has a `search_query` that maps to its emotional beat
- [ ] Scenery mood matches script section tone

**Asset feasibility:**
- [ ] Every `required_asset` has `source: "stock_photo"` — no AI generation, no diagrams
- [ ] Background images are portrait 1080×1920 (9:16) orientation
- [ ] If `background_video` type used: only ONE scene of this type, or all scenes share the same video asset

### Step 5: Submit

Validate the scene_plan against the schema and persist via checkpoint.

## Common Pitfalls

- **Using scene types not in the template**: The template defines the available scene vocabulary. If the template only allows `background_image`, do not generate `illustration_card` or `text_card` scenes.
- **Search queries too vague**: "nature" won't return good results. Use concrete descriptors: "misty mountain lake sunrise wide shot landscape photography"
- **Wrong orientation**: All background images must be portrait (1080×1920). Use `orientation: portrait` in search queries.
- **Duplicate biome**: Two ocean scenes in a row feels repetitive. Vary the scenery type between consecutive scenes.
- **Arbitrary scene windows (blocked)**: Never use round numbers (10s, 8s) for `start_seconds`/`end_seconds`. Windows must be cue-derived: start = first cue − lead_in, non-last duration = cue span + tail, last duration = cue span + last_tail (see Step 1.5 above). Arbitrary windows cause narration drift — a recurring defect.
