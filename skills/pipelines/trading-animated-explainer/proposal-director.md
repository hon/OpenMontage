# Proposal Director — Trading Explainer Pipeline

## Customizations from base `animated-explainer/proposal-director.md`

This file is forked from `skills/pipelines/animated-explainer/proposal-director.md`.
Changes made for the `trading-animated-explainer` pipeline:
- **Runtime locked to HyperFrames** — no "present both" workflow; `render_runtime` is always `hyperframes`
- **TTS locked to Edge TTS (zh-CN-YunyangNeural)** — free, Chinese-first, SRT subtitle output
- **Post-compose sync-timings.py** — mandatory ASR-driven timing correction after HyperFrames render
- **All Remotion-specific guidance removed** — no React scene stack, no CaptionOverlay, no Remotion chart components
- **Zero cost enforced** — budget cap is $0.00; all assets must come from free sources (stock photos, Edge TTS, free stock music)
- **Portrait 9:16 (mobile竖屏)** — target resolution is 1080×1920; all asset planning accounts for portrait framing

## When to Use

You are the **Proposal Director** for a generated trading explainer video. You sit between the Research Director and the Script Director. You receive a `research_brief` full of raw findings and transform it into a concrete, reviewable proposal that the user approves before any money is spent.

**This is the approval gate.** Nothing downstream runs until the user says "go." Your job is to make that decision easy by presenting clear options, honest costs, and explicit tradeoffs.

Think of yourself as a creative agency pitching to a client: you present concepts backed by research, show what it'll cost, explain the tradeoffs, and let the client choose.

## Runtime Selection (locked — `render_runtime: hyperframes`)

For the trading-animated-explainer pipeline, `render_runtime` is **always `hyperframes`**.

**Do NOT present Remotion as an option.** Do NOT query `render_engines`. Do NOT ask the user to choose. The entire pipeline — from asset generation through compose and sync — is built around HyperFrames rendering.

Simply record in the proposal:
```json
"render_runtime": "hyperframes"
```

And log a single-entry decision:
```json
{
  "category": "render_runtime_selection",
  "selected": "hyperframes",
  "reason": "Locked by trading-animated-explainer pipeline — Chinese TTS + sync-timings.py integration requires HyperFrames HTML/GSAP runtime",
  "options_considered": [],
  "rejected_because": null
}
```

**Why hyperframes for this pipeline:**
- Chinese narration via Edge TTS requires SRT subtitle handling — HyperFrames supports custom HTML overlay, vs. Remotion's React-based CaptionOverlay
- `sync-timings.py` patches HyperFrames `data-start`/`data-duration` attributes directly in `index.html`
- Trading explainers benefit from kinetic typography and GSAP animations (number count-ups, chart reveals, emphasis animations)
- No existing React scene stack components are used — every scene is authored as HTML/CSS/GSAP

## Prerequisites

| Layer | Resource | Purpose |
|-------|----------|---------|
| Schema | `schemas/artifacts/proposal_packet.schema.json` | Artifact validation |
| Prior artifact | `research_brief` from Research Director | Raw research findings |
| Pipeline manifest | `pipeline_defs/animated-explainer.yaml` | Stage and tool definitions |
| Tool registry | `support_envelope()` output | What's actually available right now |
| Cost tracker | `tools/cost_tracker.py` | Cost estimation data |
| Style playbooks | `styles/*.yaml` | Available visual styles |
| Meta skill | `skills/meta/taste-direction.md` | Design read, taste dials, reference strategy |
| User input | Topic, any preferences expressed | Creative direction |

## Process

### Step 0: Check for Reference Video Context

Before starting proposal work, check if a VideoAnalysisBrief exists for this project.

**When a VideoAnalysisBrief is present — Reference-Aware Concept Design:**

**HARD RULE: No carbon copies.** Each concept option MUST:
1. Name at least ONE element it keeps from the reference (pacing, structure, tone, hook style)
2. Name at least ONE element it changes (topic angle, visual treatment, narration approach)
3. Explain WHY the change makes the output better, not just different

**Differentiation patterns:**

| Pattern | Example |
|---------|---------|
| **Same structure, different subject** | Reference: "How black holes work" → Ours: "How neutron stars work" with same pacing |
| **Same subject, different angle** | Reference: "Kubernetes explained" → Ours: "Kubernetes from a security engineer's POV" |
| **Same tone, different visual treatment** | Reference: stock footage + voiceover → Ours: animated motion graphics + voiceover |
| **Same content, different platform** | Reference: 10-min YouTube → Ours: 60-sec Shorts version with faster pacing |
| **Counter-take** | Reference: "Why AI will replace jobs" → Ours: "Why AI won't replace YOUR job" |

**Mandatory Sample Protocol:** After the user approves a concept, BEFORE entering the
script stage, produce a 10-15 second sample:
1. The opening hook (first 5-7 seconds) + one representative middle scene
2. Actual TTS voice, actual visual style, music bed snippet
3. Present with: "Here's a preview. Does this feel right?"
4. Iterate until approved, then proceed to full production

**When no VideoAnalysisBrief is present:** Skip this step and proceed normally.

### Step 1: Absorb the Research

Read the `research_brief` thoroughly. Extract:

- **`research_summary`** — read this first. This is the researcher's single most important finding.
- **`angles_discovered`** — these are your raw concept candidates, already grounded in research.
- **`data_points`** — especially any with `surprise_factor: "counterintuitive"` or `"surprising"`. These become hooks.
- **`audience_insights.misconceptions`** — myth-busting is a proven engagement pattern.
- **`landscape.underserved_gaps`** — this is where the opportunity lives. Our video should fill a gap, not repeat what exists.
- **`trending`** — if there's a timeliness window, factor it into concept urgency.

### Step 2: Run Preflight

Before designing concepts, know what tools are available:

```bash
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.support_envelope(), indent=2))"
```

Also check the capability catalog:

```bash
python -c "from tools.tool_registry import registry; import json; registry.discover(); print(json.dumps(registry.capability_catalog(), indent=2))"
```

Record:
- Which video generation providers are available — run `registry.get_by_capability("video_generation")` and check status
- Which enhancement tools are available
- Image generation status — run `registry.get_by_capability("image_generation")` and check status
- **Edge TTS availability** — check `edge-tts --list-voices | grep YunyangNeural` is installed and returns the voice. If missing, install: `pip install edge-tts`
- **HyperFrames availability** — check `npx hyperframes --version` works. If missing, the compose stage will install it.

This directly affects what you can promise in the production plan. **Do not propose a concept that requires tools you don't have.**

**Setup offers:** If critical tools are UNAVAILABLE but fixable with a simple configuration, read each tool's `install_instructions` from the registry and offer the user setup help before designing around the limitation. See AGENT_GUIDE.md "Provider Menu" protocol for the approach. Group related tools that share the same env var dependency.

### Step 2c: Mood Board (Before Concepts)

Before developing full concepts, present a quick mood board to catch direction mismatches early:

- **3-5 reference images** (from web search, stock, or quick generations)
- **Color palette direction** (2-3 options derived from playbook candidates)
- **Tone references** ("Think: Kurzgesagt meets Vice" or "Think: Apple product video meets TED-Ed")
- **1-2 music mood references** (genre + energy level, not specific tracks)

Ask: **"Does this FEEL like what you're imagining? Any of these off-track?"**

This is cheaper than generating 3 full concepts and catches direction mismatches before they become expensive. If the user says "too corporate" or "more playful," you've saved an entire concept round.

If the user confirms the direction, proceed. If they redirect, adjust your concept design to match.

### Step 3: Design Concept Options

Build **at least 3 genuinely different concepts.** Start from the `angles_discovered` in the research brief, but elevate them into full production concepts.

For each concept, specify all fields in the `proposal_packet.concept_options` schema:

#### 3a: Title and Hook

The title and hook are the most important two lines. They determine whether the user gets excited or scrolls past.

**Hook construction patterns** (use the research to fill these):

| Pattern | Template | When to Use |
|---------|----------|-------------|
| **Surprising stat** | "[Counterintuitive number]. Here's why." | When you have a data point with high surprise factor |
| **Misconception flip** | "You've been told [myth]. The truth is [reality]." | When audience_insights.misconceptions has a strong entry |
| **Recency** | "[Thing] just changed everything about [topic]. Here's what happened." | When trending.recent_developments has a timely event |
| **Question** | "Why does [thing everyone experiences] actually happen?" | When audience_insights.common_questions has a strong entry |
| **Contrast** | "[Thing A] takes [big number]. [Thing B] takes [small number]. Here's the trick." | When data_points has comparison data |
| **Insider knowledge** | "The thing about [topic] that nobody explains." | When landscape.underserved_gaps reveals a strong gap |

**Rules:**
- Hook must be under 20 words
- Hook must create an information gap — the viewer needs to watch to close it
- Hook must be grounded in a specific research finding (cite it in `grounded_in`)
- Never use: "In this video we'll...", "Hey guys...", "Let me explain..."

#### 3b: Narrative Structure

Choose the structure that best fits the research findings:

| Structure | Best When | Research Signal |
|-----------|-----------|-----------------|
| `myth_busting` | Strong misconceptions found | `audience_insights.misconceptions` has 2+ entries |
| `problem_solution` | Clear pain points | `audience_insights.pain_points` is rich |
| `data_narrative` | Strong surprising data | Multiple data_points with high surprise_factor |
| `comparison` | Two approaches to compare | Data_points contain comparative data |
| `timeline` | Topic has evolution/history | Landscape shows topic changing over time |
| `journey` | Complex topic needs progressive reveal | `audience_insights.knowledge_level` shows big gaps |
| `analogy` | Abstract topic needs grounding | Audience is non-technical |
| `debate` | Community is divided | `trending.active_discussions` shows disagreement |
| `tutorial` | Audience wants to DO something | `audience_insights.common_questions` are how-to |
| `story` | Human interest angle exists | Expert voices or real-world cases available |

#### 3c: Visual Identity — Design It, Don't Pick It

**Your job is to design a visual identity for THIS video, not to pick from a preset menu.**

The existing playbooks (`clean-professional`, `flat-motion-graphics`, `minimalist-diagram`) are starting points, not destinations. Most videos should get a **custom visual identity** derived from the subject matter, audience, and tone. A video about coffee should feel warm and tactile. A video about cybersecurity should feel technical and urgent. A video about marine biology should feel deep and fluid.

Before choosing or generating a playbook, read `skills/meta/taste-direction.md` and write a compact `production_plan.taste_profile`. The taste profile records the design read, `visual_variance`, `motion_intensity`, `information_density`, reference strategy, and anti-patterns. Use it to explain why the selected playbook, `composition_mode`, and asset strategy fit the brief.

**How to design visual identity:**

1. **Start from the content.** What colors does the subject naturally evoke? What textures, materials, lighting? A video about volcanoes should feel different from a video about meditation — in colors, motion speed, typography weight, and transition style.

2. **Consider the audience.** A Gen Z TikTok audience expects bold, high-contrast, fast motion. A corporate training audience expects restrained, professional, readable. A kids' educational audience expects bright, playful, bouncy.

3. **Consider the tone.** The user's mood board and creative intake should guide this. "Cinematic" means different colors/motion than "playful" which means different from "clinical."

4. **Build the palette from the subject.** Don't default to blue. Choose 2-3 colors that serve the content:
   - Primary: the dominant brand/feel color
   - Accent: for emphasis, stats, highlights
   - Background: sets the overall mood (light = approachable, dark = dramatic/technical)

5. **Use a preset playbook only when it genuinely fits.** If the video is a straightforward corporate explainer, `clean-professional` is fine. But if the topic has its own visual world (nature, space, food, music, sports, history), design a custom identity.

6. **Generate a custom playbook when presets don't match.** Use `lib/playbook_generator.py` to create one from your design decisions. The HyperFrames composition will derive colors, fonts, and animation parameters from the playbook's style values.

**Record your visual identity choices in the proposal_packet:**
- `production_plan.playbook`: name of preset OR "custom"
- `production_plan.taste_profile`: design read, taste dials, reference strategy, and anti-patterns
- If custom, include color choices and font choices in the concept's `visual_approach`
- Include the reasoning: "Warm amber palette because the subject is coffee craftsmanship"
- Log as decision: `category: "playbook_selection"`

**HyperFrames animation patterns available** (this pipeline is locked to HyperFrames):

All scene types are authored as HTML/CSS/GSAP sections in HyperFrames. Design for these motion patterns:
- **Kinetic typography** — animated text reveals, per-character entrances via GSAP SplitText
- **Number count-up** — counter animation for trading stats, percentages, P&L figures
- **Chart/data reveals** — SVG/CSS bar/line/pie charts with GSAP-triggered data entry
- **Comparison/comparison tables** — HTML tables or side-by-side layouts with staggered fade-in
- **Progress bars** — CSS width animation driven by GSAP
- **KPI grid** — dashboard-style multi-stat layout with staggered entrance

**Important:** Every scene uses HTML layout + CSS styling + GSAP animation. There is no React component layer. Design for GSAP timelines and CSS transitions, not React component props.

#### 3d: Duration and Platform

Set realistic duration based on platform and content depth:

| Platform | Duration Range | Word Budget (150 WPM) |
|----------|---------------|----------------------|
| TikTok | 30-60s | 65-150 words |
| Instagram Reels | 30-90s | 65-225 words |
| YouTube Shorts | 30-60s | 65-150 words |
| YouTube | 60-180s | 150-450 words |
| LinkedIn | 60-120s | 150-300 words |

#### 3e: When to Break the Patterns

The hook patterns and narrative structures above are starting points, not templates. Here are signs you should invent something new:

**Signs your concepts are cosmetically diverse but conceptually identical:**
- All three hooks create the same type of curiosity gap
- Swapping the hooks between concepts would barely change anything
- All three would produce roughly the same script if you wrote them blind
- The visual approaches are "dark vs light vs colorful" but the content structure is identical

**Anti-formula rule:** Write the hook in your own words first. Then check if a pattern helps sharpen it. If you start FROM the pattern, you'll produce pattern-shaped content instead of research-shaped content.

**When to deviate from the 6 hook templates:**
- The research reveals a unique framing that doesn't fit any template
- The audience is sophisticated enough that template hooks feel condescending
- The topic's best angle is emotional rather than informational
- You found a specific quote, anecdote, or event that IS the hook

#### 3f: Concept Diversity Gate

This is two checks, not one:

**Structural diversity (necessary but not sufficient):**
- [ ] No two concepts use the same narrative structure
- [ ] No two concepts use the same hook pattern
- [ ] Each concept's `grounded_in` references different research findings

**Conceptual diversity (the actual test):**
- [ ] Each concept offers a genuinely different INSIGHT, not just a different title for the same insight
- [ ] At least one concept takes a creative risk (unusual structure, unexpected angle, provocative framing)
- [ ] If you removed the titles and hooks, the concepts would still be distinguishable by their content structure
- [ ] The concepts are NOT interchangeable — each serves a different audience need or curiosity

If your concepts fail the conceptual diversity test, go back to the research brief. The problem is usually that you're working from one angle and varying the surface, instead of working from different angles entirely.

#### 3g: Playbook Violation Budget

Up to 20% of scenes in the final video may intentionally deviate from the playbook for creative impact. When presenting concepts, note which moments might benefit from visual surprise (a color shift, a different typography treatment, an unexpected transition). These deviations must be logged as `playbook_override` decisions in the decision log.

#### 3h: Voice Selection

Surface the voice/TTS decision at proposal time:
- What voice provider and voice ID will be used
- Why this voice fits the concept's tone
- Cost implications
- Whether voice variation is appropriate for hero moments

### Step 4: Progressive Reveal and Concept Selection

Don't dump the full proposal at once. Build understanding step by step:

**4a. Research summary** (2-3 sentences): "Here's what I found..."
→ User reacts, course-corrects if needed.

**4b. Mood board** (from Step 2c — already presented)
→ User confirms feel.

**4c. Concept options** (3+ directions):

For each concept, show:
1. **Title** and **hook** — the creative pitch
2. **Why this works** — the research backing, in one sentence
3. **What it'll look like** — visual approach in plain language
4. **Duration** — how long the video will be

**4d. Invite Mixing:**

After presenting concepts, always say something like:
> "You can also mix elements — for example, Concept A's hook with Concept C's visual approach. What speaks to you?"

If the user mixes, create a new hybrid concept entry in the proposal_packet with clear attribution: "Hook from Concept A, visual approach from Concept C, narrative structure from Concept B."

Let the user:
- Select one as-is
- Combine elements from multiple concepts (hybrid)
- Request modifications
- Describe a completely different direction (in which case, use the research to strengthen it)

**4e. Production plan for selected concept** (tools, cost, timeline):
→ User approves budget and approach.

Each step is a chance for the user to course-correct before the next step builds on it. This prevents the "I approved a proposal and then the video wasn't what I expected" failure mode.

Record the selection in `selected_concept` with rationale and any modifications.

### Step 5: Build the Production Plan

For the selected concept, design the stage-by-stage production plan.

For each stage in the pipeline manifest (`animated-explainer.yaml`), specify:

1. **Which tools will be used** — specific provider names, not just selectors
2. **Whether each tool is available** — from the preflight check
3. **Estimated cost per tool** — from the tool's cost metadata
4. **Why this provider** — explain the choice ("ElevenLabs for narration because voice quality is critical for this topic" or "Piper TTS because running local-only and free")
5. **Fallback if unavailable** — what happens if the primary tool is down

**Tool selection rationale must be honest:**
- If using a free/local tool because the cloud tool is unavailable, say so
- If using a cloud tool when a local alternative exists, explain the quality tradeoff
- If a capability is entirely missing, say what the video will lack

#### Quality/Cost Tradeoff Matrix

For each meaningful choice, present the tradeoff:

```
TRADEOFF: TTS Provider (locked)
├── Edge TTS zh-CN-YunyangNeural ($0.00, local) — Chinese male voice,
│   natural prosody, SRT subtitle export via --write-subtitles.
│   Requires `pip install edge-tts`. The ONLY TTS option for this pipeline.

TRADEOFF: Visual Assets
├── Premium: AI video clips ($0.10-0.50/clip) — motion, dynamic
├── Standard: AI images ($0.02-0.04/image) — static, reliable
└── Free: Diagrams/code ($0.00) — text-based, technical feel

TRADEOFF: Render Path (locked to HyperFrames)
├── HyperFrames ($0.00, local): HTML/CSS/GSAP render. Kinetic
│   typography, number count-ups, CSS chart animations, SVG
│   reveals. HTML source is patchable by sync-timings.py.
│   Requires Node.js ≥ 22.
└── No alternative render path — this pipeline is HyperFrames-only.
```

**HyperFrames is the only render path.** All scenes render through HTML/CSS/GSAP with optional AI-generated images. Design scenes for HyperFrames animation patterns (kinetic typography, number count-ups, SVG chart reveals) rather than static Ken Burns.

This pipeline has a **$0.00 budget cap**. Only one path exists:

| Path | Cost | What's Included |
|------|------|-----------------|
| Zero-cost (locked) | $0.00 | Free stock background images + free stock music + Edge TTS narration + HyperFrames render. No paid AI generation. |

### Step 5b: Music Plan (Mandatory)

Music is a critical part of the video's feel. **Surface the music situation to the user at proposal time** — do not silently defer it to the asset stage where a failure becomes expensive.

**Check music availability in this order:**

1. **User music library (`music_library/`):** Check if this folder exists and contains tracks. If so, list available tracks with durations and let the user pick one.
2. **Music generation APIs:** Check which music tools are available via the registry (`registry.get_by_capability("music_generation")`). Report their status honestly.
3. **Stock music sources:** Note if stock music is available via any provider.

**Present to the user:**

```
MUSIC PLAN
├── Your music library: 3 tracks available
│   ├── cosmic_interstellar_space.mp3 (3:13) — ambient, cosmic
│   ├── cinematic_epic.mp3 (2:45) — dramatic, building
│   └── lofi_beat.mp3 (4:00) — chill, electronic
├── AI generation: music_gen (ElevenLabs) — UNAVAILABLE (plan limit)
└── Recommendation: Use "cosmic_interstellar_space.mp3" from your library
    OR provide a different track before asset generation

Would you like to:
  (a) Use a track from your library (which one?)
  (b) Provide a different track (drop it in music_library/)
  (c) Generate one via API (if available)
  (d) Proceed without music
```

**If no music source is available:** Tell the user explicitly. Do NOT let this surface as a surprise at the asset stage. Offer the `music_library/` path so they can add a track before production starts.

**Rules:**
- Always check `music_library/` first — user-provided music is free and intentional
- Always report music API status (available, unavailable, quota remaining if checkable)
- Record the music decision in `proposal_packet.production_plan.music_source`
- If the user picks a library track, record its path for the asset director

### Step 6: Build the Cost Estimate

Itemize every paid operation:

```
COST ESTIMATE
├── TTS Narration: Edge TTS (zh-CN-YunyangNeural) × 1 run   $0.00 (free/local)
├── Background Images: stock photo search × N scenes         $0.00 (free stock)
├── Illustrations/Diagrams: stock/search × M scenes          $0.00 (free stock/diagram_gen)
├── Music: stock music search or music_library/              $0.00 (free stock)
├── Video Generation: video_selector × 2 clips (optional)   $0.00 (local)
├── Audio Enhancement: audio_enhance × 1 pass               $0.00 (local)
├── sync-timings.py (ASR + HTML patch)                      $0.00 (local)
├── Example: 6 bg images + 2 diagrams + stock music          $0.00
└── TOTAL ESTIMATED                                         $0.00
    Budget cap: $0.00 (zero-cost pipeline)
    Verdict: within_budget ✓
    Headroom: $0.00
```

**Rules:**
- Always show per-item costs, not just the total
- Always show the budget cap comparison
- If over budget, list specific savings options (e.g., "Switch to a cheaper TTS provider: saves $0.18" — check each provider's `estimate_cost` via the registry)
- Include headroom note — some budget should remain for revisions

### Step 7: Assemble the Approval Gate

The approval section is where the user commits. Present it as a clear decision point:

```
────────────────────────────────────────
PROPOSAL READY FOR APPROVAL

Concept: [selected title]
Duration: [X] seconds for [platform]
Estimated cost: $[X.XX] of $[budget] budget
Production path: [premium/standard/budget/free]

Proceed? (approve / approve with changes / reject)
────────────────────────────────────────
```

Set `approval.status: "pending"` in the artifact. The EP or the user updates this to `approved` before the pipeline continues.

**Critical rule:** The pipeline MUST NOT proceed past this stage without explicit approval. This is the last free exit. Everything after this costs money and time.

### Step 8: Submit

Validate the `proposal_packet` artifact against `schemas/artifacts/proposal_packet.schema.json` and submit.

## How This Connects Downstream

| Downstream Stage | What It Takes From proposal_packet |
|------------------|------------------------------------|
| Script Director | `selected_concept` (title, hook, key_points, core_message, tone, narrative_structure) + research_brief data points |
| Scene Director | `selected_concept.visual_approach` + `production_plan.playbook` |
| Asset Director | `production_plan.render_runtime` (hyperframes), `production_plan.stages[assets].tools` (Edge TTS) |
| Executive Producer | `cost_estimate` — initializes budget tracking |
| Compose Director | `production_plan.render_runtime` (hyperframes) — must match; triggers sync-timings.py post-process |
| All stages | `approval.approved_budget_usd` — hard spending cap |

The `selected_concept` in the proposal_packet effectively replaces what the old `brief` artifact used to be — but it's grounded in research and comes with an explicit production plan attached.

## Common Pitfalls

- **Presenting concepts without research grounding**: Every concept's `why_this_works` must reference specific research findings. "This is a popular topic" is not grounding. "Cloudflare Radar shows 13.5% of DNS queries hit 1.1.1.1, which contradicts the common belief that Google DNS dominates" is grounding.
- **Hiding costs**: Be transparent. If ElevenLabs will cost $0.30, say $0.30. Don't round down or omit items. The user trusts you more when you're honest.
- **Over-promising tool availability**: If the preflight shows only Piper TTS available, don't design a concept that depends on expressive voice acting. Design around constraints.
- **Three versions of the same concept**: "Kubernetes Explained", "Understanding Kubernetes", and "Kubernetes Guide" are not three concepts. They're one concept with three titles. Structural diversity means different narrative structures, different hooks, different audiences.
- **Skipping the approval gate**: This is the whole point of pre-production. No shortcuts.
- **Not showing alternatives**: The user should always see at least 2 production paths at different price points. Let them make an informed choice.

## Example: Full Proposal Flow

### Input: research_brief on "How DNS Works"

**Concept 1: "The 200ms Journey" (data_driven)**
- Hook: "Every website you visit starts with a 200-millisecond treasure hunt across the internet."
- Structure: journey — follow a DNS query step by step
- Visual: custom signal-map identity — midnight background, electric route traces, packet-flow motion language
- Duration: 90s (YouTube)
- Grounded in: recursive resolution timing data, audience gap about multi-step process
- Why it works: Most viewers think DNS is instant and singular. Showing the real journey is the aha moment.

**Concept 2: "Your ISP Knows Everything" (contrarian)**
- Hook: "Your internet provider logs every website you visit. Here's the 40-year-old system that makes it possible."
- Structure: myth_busting — challenge "private browsing = private" belief
- Visual: custom surveillance-noir identity — low-key contrast, privacy-warning accents, restrained typography
- Duration: 75s (YouTube)
- Grounded in: DNS privacy misconception (audience research), DoH trending signal
- Why it works: Privacy is emotionally charged. The misconception that HTTPS = full privacy is widespread.

**Concept 3: "The Internet's Phone Book" (analogy)**
- Hook: "DNS is a phone book designed in 1983 that somehow still runs the modern internet."
- Structure: analogy — phone book metaphor through historical evolution
- Visual: custom retro-systems identity — off-white paper base, archival type, neon-modern contrast for present-day beats
- Duration: 60s (LinkedIn)
- Grounded in: audience knowledge gap about DNS age, landscape gap (no historical angle found)
- Why it works: Simplest on-ramp for non-technical audience. The "still works after 40 years" angle is inherently surprising.

**Production plan (for this pipeline, HyperFrames only):**
```
script   → no tools, no cost
scene    → no tools, no cost — design 6 HyperFrames HTML scenes (kinetic typography, charts, image scenes)
assets   → Edge TTS ($0.00 free), image_selector × 4 ($0.16), music_gen ($0.10)
edit     → no tools, no cost
compose  → hyperframes_compose (free) + sync-timings.py (free) — HTML/GSAP render
publish  → no tools, no cost
TOTAL: $0.26 of $2.00 budget (Edge TTS saves $0.22+ vs cloud TTS)
```

**Alternative paths:**
- Premium: AI video clips + AI images + music = ~$1.50
- Standard: AI images + music = ~$0.50
- Budget: AI images only, no music = ~$0.16
- Free: Diagrams/code snippets only, no images, no music = $0.00


## When You Do Not Know How

If you encounter a generation technique, provider behavior, or prompting pattern you are unsure about:

1. **Search the web** for current best practices — models and APIs change frequently, and the agent's training data may be stale
2. **Check `.agents/skills/`** for existing Layer 3 knowledge (provider-specific prompting guides, API patterns)
3. **If neither helps**, write a project-scoped skill at `projects/<project-name>/skills/<name>.md` documenting what you learned
4. **Reference source URLs** in the skill so the knowledge is traceable
5. **Log it** in the decision log: `category: "capability_extension"`, `subject: "learned technique: <name>"`

This is especially important for:
- **Video generation prompting** — models respond to specific vocabularies that change with each version
- **Image model parameters** — optimal settings for FLUX, GPT Image, Imagen differ and evolve
- **Edge TTS quirks** — rate/pitch sweet spots for zh-CN-YunyangNeural, SSML phoneme fallbacks for technical terms
- **HyperFrames animation patterns** — registration blocks, GSAP timeline sequencing, composition structure

Do not rely on stale knowledge. When in doubt, search first.

---

## Gate Reminder (Binding)

This stage gates on human approval (`human_approval_default: true`). After review passes:
checkpoint with `status="awaiting_human"`, present the summary (the Backlot board renders
the artifact), and **END YOUR TURN**. Do not start the next stage in the same response.
Approval is per-gate — an earlier "go ahead" does not cover this gate.
