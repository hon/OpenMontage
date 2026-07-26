# Scene Director — Trading Explainer Pipeline

## Customizations from base `animated-explainer/scene-director.md`

This file is forked from `skills/pipelines/animated-explainer/scene-director.md`.
Changes made for the `trading-animated-explainer` pipeline:
- **Simple template mode** — only two scene types: `background_image` and `background_video`. No Remotion scenes.
- **No animations** — scenes are text-over-background only. No diagram reveals, no data dashboards, no stat cards.
- **1 scene = 1 script section** — no need to split sections into multiple visual types.
- **Zero-cost stock images** — backgrounds sourced from stock photo APIs only; only `description` and `search_query` matter.

## When to Use

You are the Scene Planner for a generated trading explainer video. You have a `script` artifact with timestamped sections. Your job is to map each script section to a background image (or video) and define what text appears on screen.

This pipeline uses a **fixed template**: full-screen background + centered sentence text. Only the background and text content change per scene.

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/scene_plan.schema.json` | Artifact validation |
| Prior artifacts | `state.artifacts["script"]["script"]`, `state.artifacts["proposal"]["proposal_packet"]` | Script sections and proposal packet |
| Playbook | Active style playbook | Visual language, transitions, motion rules |

## Process

### Step 1: Analyze the Script

Read every section. For each, note:
- What concept is being explained?
- What is the emotional beat? (calm/educational, serious/weighty, hopeful/inspiring, neutral/general)
- How much time is available? (end_seconds - start_seconds)

### Step 2: Define Background for Each Section

Each script section maps to **exactly one scene**. Choose a natural scenery mood that matches the emotional beat:

| Script Mood | Recommended Scenery | Stock Search Hint |
|---|---|---|
| Calm/educational | Misty mountains, still lake, sunrise over forest | `"misty mountain lake sunrise landscape"` |
| Serious/weighty | Deep canyon, rocky cliff, night starscape | `"dramatic canyon twilight landscape"` |
| Hopeful/inspiring | Sunlight through trees, golden hour field, rainbow | `"golden hour forest sunlight warm"` |
| Urgent/exciting | Storm clouds, ocean waves, thunder sky | `"dramatic storm ocean waves dark sky"` |
| Neutral/general | Lush green hills, waterfall, autumn forest | `"lush rolling hills morning light landscape"` |

### Step 3: Build Scene Objects (Simplified)

Each scene is a simple text-over-background frame:

```json
{
  "id": "scene-1",
  "type": "background_image",
  "description": "Misty mountain lake at sunrise — calm, reflective mood for introduction",
  "search_query": "misty mountain lake sunrise landscape",
  "start_seconds": 0.0,
  "end_seconds": 10.0,
  "script_section_id": "s1",
  "transition_in": "fade",
  "transition_out": "fade",
  "required_assets": [
    {
      "type": "image",
      "subtype": "background",
      "description": "Misty mountain lake at sunrise, high resolution, landscape",
      "source": "stock_photo"
    }
  ]
}
```

#### Scene Types (only two)

| Type | Best For | Asset Required |
|------|----------|----------------|
| `background_image` | All script sections (default) | Per-scene stock photo, portrait 1080×1920 |
| `background_video` | Full-duration single background | Single MP4 background video (loops if shorter than narration) |

- `background_image` is the **default** for all scenes
- `background_video` is used **only** when a suitable free-license background video is found (e.g., Pixabay video). In that case, ONE video asset serves ALL scenes and each scene just changes which text is displayed.

**No other scene types exist in this pipeline.** Do not generate `diagram`, `chart`, `stat_card`, `text_card`, `hero_title`, `animation`, or any other type.

### Step 4: Validate

**Coverage check:**
- [ ] Scenes span the full script duration (first scene starts at 0s, last scene ends at total_duration)
- [ ] Every script section has exactly one corresponding scene
- [ ] No gaps > 1s between scenes

**Background consistency:**
- [ ] No two consecutive scenes use the same biome (vary mountain/ocean/forest/canyon/lake)
- [ ] Each scene has a `search_query` that maps to its emotional beat
- [ ] Scenery mood matches script section tone

**Asset feasibility:**
- [ ] Every `required_asset` has `source: "stock_photo"` — no AI generation, no diagrams
- [ ] Background images are portrait 1080×1920 (9:16) orientation
- [ ] If `background_video` type used: only ONE scene of this type, or all scenes share the same video asset

### Step 5: Submit

Call `handle_explainer_scene_plan(state, {"scene_plan": scene_plan_json})` to validate and persist.

## Common Pitfalls

- **Adding animation**: Do NOT add scene types beyond `background_image`/`background_video`. No chart, diagram, stat card, or animated scenes.
- **Multiple scenes per section**: Each script section maps to exactly ONE scene. The text changes per sentence within a scene (handled by compose stage), not per visual scene.
- **Ignoring mood**: A section about "risk of loss" should not have a bright sunny beach background. Match mood to scenery.
- **Vague search queries**: "Misty mountain lake at sunrise, high resolution landscape photograph" is useful. "Nature" is not.
- **Inconsistent orientation**: All background images must be portrait 1080×1920 for the 9:16 vertical format.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
