#!/usr/bin/env python3
"""
sync-timings.py — ASR-driven narration-to-text timing corrector for HyperFrames projects.

Problem: HyperFrames index.html scene timings (data-start, data-duration, GSAP timeline
positions) are often hand-guessed, causing desync between narration audio and on-screen text.

This script:
  1. Transcribes the narration audio with mlx_whisper (word-level timestamps)
  2. Parses scene text content from the project's index.html
  3. Matches each scene to its corresponding ASR segment via fuzzy text matching
  4. Computes correct data-start, data-duration, and GSAP timeline positions
  5. Patches the index.html in-place with corrected values

Usage:
  # Fix a project (runs ASR, patches index.html)
  python scripts/sync-timings.py projects/trading-psychology

  # Dry-run: print report only, don't modify
  python scripts/sync-timings.py projects/trading-psychology --dry-run

  # Use pre-computed ASR JSON (skip re-transcription)
  python scripts/sync-timings.py projects/trading-psychology --asr-json /tmp/result.json

  # Custom narration path (default: assets/audio/narration.mp3)
  python scripts/sync-timings.py projects/my-video --narration assets/audio/voiceover.mp3

Dependencies: pip install mlx-whisper  (Apple Silicon only)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. ASR — run mlx_whisper on narration audio
# ---------------------------------------------------------------------------

def find_mlx_whisper():
    """Locate mlx_whisper binary or fall back to python -m mlx_whisper."""
    candidates = [
        "mlx_whisper",
        "python3 -m mlx_whisper",
        "python -m mlx_whisper",
    ]
    for c in candidates:
        try:
            subprocess.run(c.split()[0], capture_output=True, timeout=5)
            return c
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def run_asr(audio_path: str, output_dir: str) -> dict:
    """Run mlx_whisper on audio_path, return parsed JSON result dict."""
    audio_path = str(Path(audio_path).resolve())
    os.makedirs(output_dir, exist_ok=True)

    # Try using cached tiny model first
    cache_base = Path.home() / ".cache" / "huggingface" / "hub"
    cached_models = list(cache_base.glob("models--mlx-community--whisper-*"))
    model_arg = None
    for m in sorted(cached_models, reverse=True):
        snapshots = list(m.glob("snapshots/*"))
        if snapshots:
            model_arg = str(snapshots[0])
            break

    cmd = [
        sys.executable, "-c", f"""
import mlx_whisper, json, sys
result = mlx_whisper.transcribe(
    {json.dumps(audio_path)},
    path_or_hf_repo={json.dumps(model_arg) if model_arg else 'None'},
    language='zh',
    word_timestamps=True,
    fp16=True,
)
json.dump(result, sys.stdout, ensure_ascii=False)
"""
    ]

    print(f"  Transcribing {audio_path} …")
    if model_arg:
        print(f"  Using cached model: {model_arg}")

    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if out.returncode != 0:
            print(f"  ASR stderr: {out.stderr[:500]}", file=sys.stderr)
            raise RuntimeError(f"mlx_whisper failed (exit {out.returncode})")
        result = json.loads(out.stdout)
    except json.JSONDecodeError as e:
        print(f"  Failed to parse ASR output: {e}", file=sys.stderr)
        print(f"  Raw output (first 500 chars): {out.stdout[:500]}", file=sys.stderr)
        raise

    # Save copy
    out_path = os.path.join(output_dir, "asr_result.json")
    with open(out_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  ASR result saved to {out_path}")
    return result


def load_asr(json_path: str) -> dict:
    """Load pre-computed ASR JSON."""
    with open(json_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# 2. Parse scene text from index.html
# ---------------------------------------------------------------------------

def parse_html_scenes(html_path: str) -> list[dict]:
    """Parse scene sections from a HyperFrames index.html.

    Returns list of dicts:
      { id: str, tag: str, data_start: float, data_duration: float,
        text_lines: list[str], full_text: str }
    """
    with open(html_path) as f:
        html = f.read()

    scenes = []

    # Find all <section class="clip text-clip" ...> blocks
    pattern = re.compile(
        r'<section\s+[^>]*id="([^"]*)"[^>]*class="[^"]*\bclip\b[^"]*\btext-clip\b[^"]*"[^>]*'
        r'data-start="([^"]*)"[^>]*data-duration="([^"]*)"[^>]*>(.*?)</section>',
        re.DOTALL,
    )

    for m in pattern.finditer(html):
        sid = m.group(1)
        data_start = float(m.group(2))
        data_duration = float(m.group(3))
        inner = m.group(4)

        # Extract visible text: strip all HTML tags, keep text content
        rawtext = re.sub(r'<[^>]+>', '\n', inner)
        lines = [ln.strip() for ln in rawtext.split('\n') if ln.strip()]
        text_lines = lines
        full_text = "".join(lines)
        scenes.append({
            "id": sid,
            "data_start": data_start,
            "data_duration": data_duration,
            "text_lines": text_lines,
            "full_text": full_text,
        })

    return scenes


# ---------------------------------------------------------------------------
# 3. Match scenes to ASR segments via text similarity
# ---------------------------------------------------------------------------

def normalize_text(s: str) -> str:
    """Remove whitespace, punctuation, and lowercase for matching."""
    s = re.sub(r'[\s,，。、！？：；""\'\'（）()\.\!\?\-]', '', s)
    return s.lower()


def char_overlap(a: str, b: str) -> float:
    """Character-set Jaccard similarity — handles Chinese homophone ASR errors."""
    a_set = set(normalize_text(a))
    b_set = set(normalize_text(b))
    if not a_set or not b_set:
        return 0.0
    intersection = a_set & b_set
    union = a_set | b_set
    return len(intersection) / len(union)


def match_scenes_to_segments(scenes: list[dict], segments: list[dict]) -> list[dict]:
    """Greedy sequential matching: walk scenes and segments in order.

    Both scenes and ASR segments are chronological. For each scene in order,
    try to match the widest window of upcoming segments that best covers
    the scene text. Once consumed, a segment is not reused by a later scene.

    Returns list of dicts augmented with:
      { ..., asr_start: float, asr_end: float, confidence: float }
    """
    matched = []
    seg_idx = 0
    n_segs = len(segments)

    for scene in scenes:
        target = scene["full_text"]
        best_score = 0
        best_start = None
        best_end = None
        best_count = 1

        # Try consuming 1, 2, or 3 consecutive un-consumed segments
        for k in (1, 2, 3):
            if seg_idx + k > n_segs:
                break
            combined = "".join(segments[seg_idx + j].get("text", "") for j in range(k))
            score = char_overlap(target, combined)
            if score > best_score:
                best_score = score
                best_start = segments[seg_idx]["start"]
                best_end = segments[seg_idx + k - 1]["end"]
                best_count = k

        # Fallback: if no good match, still consume at least 1 segment
        if best_start is None:
            if seg_idx < n_segs:
                best_start = segments[seg_idx]["start"]
                best_end = segments[seg_idx]["end"]
                best_count = 1
            else:
                # No segments left — use the previous segment's end as a rough point
                matched.append({
                    **scene,
                    "asr_start": segments[-1]["end"] if segments else 0,
                    "asr_end": segments[-1]["end"] + 0.5 if segments else 0.5,
                    "confidence": 0.0,
                })
                continue

        matched.append({
            **scene,
            "asr_start": best_start,
            "asr_end": best_end,
            "confidence": best_score,
        })

        # Advance segment pointer
        seg_idx += best_count

    return matched


# ---------------------------------------------------------------------------
# 4. Compute corrected timing values
# ---------------------------------------------------------------------------

def compute_timings(matched: list[dict], total_duration: float) -> list[dict]:
    """Compute new data-start, data-duration, and GSAP timeline positions.

    Fade-in: starts at data-start (= nar_start - 0.3, when element enters DOM).
    The from() tween sets opacity:0 immediately → animates to 1 → no flash.

    Fade-out: starts at nar_end - 0.5, completes at nar_end.
    Next scene's fade-in starts at its data-start (= nar_start_next - 0.3).
    For contiguous narration (nar_end_N == nar_start_N+1):
      - Scene N fully hidden at nar_end_N
      - Scene N+1 fade-in started at nar_end_N - 0.3 (minor 0.3s overlap at low opacity)

    Last scene: holds full opacity until nar_end, then fades out over the tail.
    """
    result = []
    for i, scene in enumerate(matched):
        asr_start = scene["asr_start"]
        asr_end = scene["asr_end"]

        # data-start: 0.3s before narration starts (for fade-in animation)
        new_start = max(0, asr_start - 0.3)

        nar_dur = asr_end - asr_start

        is_last = (i == len(matched) - 1)

        if is_last:
            # Last scene: text holds until nar_end, then fades out
            gsap_fade_in = new_start
            gsap_fade_out = asr_end       # start fading at last word end
            # clip covers: lead-in + narration + fade-out tail
            new_duration = nar_dur + 0.3 + 0.5
        else:
            # Regular scene: fade-out completes before next scene starts
            gsap_fade_in = new_start
            gsap_fade_out = asr_end - 0.5  # start fading 0.5s before speech ends
            # clip covers: lead-in + narration (fade-out happens inside nar_dur)
            new_duration = nar_dur + 0.3

        # Safety clamp: fade-out can't start before fade-in
        if gsap_fade_out < gsap_fade_in:
            gsap_fade_out = gsap_fade_in

        result.append({
            **scene,
            "new_start": round(new_start, 3),
            "new_duration": round(new_duration, 3),
            "gsap_fade_in": round(gsap_fade_in, 3),
            "gsap_fade_out": round(gsap_fade_out, 3),
            "nar_start": round(asr_start, 3),
            "nar_end": round(asr_end, 3),
        })

    return result


# ---------------------------------------------------------------------------
# 5. Patch index.html with corrected timings
# ---------------------------------------------------------------------------

def patch_html(html_path: str, timings: list[dict], dry_run: bool = False) -> str:
    """Rewrite data-start, data-duration in HTML sections, and GSAP timeline calls.

    Returns the patched HTML content (or prints diff if dry-run).
    """
    with open(html_path) as f:
        html = f.read()

    original = html

    # Patch data-start and data-duration on each scene section
    for t in timings:
        sid = t["id"]
        new_start = t["new_start"]
        new_dur = t["new_duration"]

        # Patch data-start
        old_pattern = re.compile(rf'(id="{re.escape(sid)}"[^>]*)data-start="[^"]*"')
        html = old_pattern.sub(
            lambda m: m.group(1) + f'data-start="{new_start}"',
            html)

        # Patch data-duration on the SAME section tag
        escaped_start = re.escape(str(new_start))
        old_pattern2 = re.compile(rf'(id="{re.escape(sid)}"[^>]*data-start="{escaped_start}"[^>]*)data-duration="[^"]*"')
        html = old_pattern2.sub(
            lambda m: m.group(1) + f'data-duration="{new_dur}"',
            html)

        # Also patch the comment annotation line if present (e.g., <!-- N. text (0-3.5s, spoken ...) -->)
        # This is cosmetic but keeps the source readable
        comment_pattern = rf'(<!--\s*{re.escape(sid)}\b.*?)spoken[^)]*\)'
        nar_start_str = f"{t['nar_start']:.3f}"
        nar_end_str = f"{t['nar_end']:.3f}"
        html = re.sub(
            comment_pattern,
            lambda m: m.group(1) + f"spoken {nar_start_str}-{nar_end_str}, sync'd)",
            html,
        )

    # Patch GSAP timeline positions (tl.from and tl.to calls for each scene)
    for t in timings:
        sid = t["id"]
        fi = t["gsap_fade_in"]
        fo = t["gsap_fade_out"]
        ds = t["new_start"]
        de = t["new_start"] + t["new_duration"]

        # Patch tl.from calls for this scene
        escaped_sid = re.escape(sid)
        # Pattern: tl.from("...#sid ...", { ... }, time)
        # The "#" is a CSS selector hash prefix, always present in HyperFrames
        from_pat = re.compile(
            r'(tl\.from\s*\(\s*"[#]' + escaped_sid + r'[^)]*?,\s*\{[^}]*\}[^)]*?,\s*)([\d.]+)(\s*\))'
        )
        html = from_pat.sub(lambda m: m.group(1) + str(fi) + m.group(3), html)

        # Patch tl.to calls for this scene (fade-out targeting .scene-inner)
        to_pat = re.compile(
            r'(tl\.to\s*\(\s*"[#]' + escaped_sid + r'[^)]*?scene-inner[^)]*?,\s*\{[^}]*\}[^)]*?,\s*)([\d.]+)(\s*\))'
        )
        html = to_pat.sub(lambda m: m.group(1) + str(round(fo, 3)) + m.group(3), html)

        # Fix set calls that hide after fade-out
        set_pat = re.compile(
            r'(tl\.set\s*\(\s*"[#]' + escaped_sid + r'[^)]*?scene-inner[^)]*?,\s*\{[^}]*\}[^)]*?,\s*)([\d.]+)(\s*\))'
        )
        html = set_pat.sub(lambda m: m.group(1) + str(round(de, 3)) + m.group(3), html)

    # Patch root composition data-duration to cover all scenes
    total_dur = max(t["new_start"] + t["new_duration"] for t in timings)
    html = re.sub(
        r'(id="root"[^>]*data-duration=")[^"]*(")',
        lambda m: m.group(1) + f"{total_dur:.3f}" + m.group(2),
        html,
    )

    # Patch audio elements' data-duration to match real file length
    import subprocess as _sp
    for audio_id in ("narration", "bgm"):
        audio_path = str(Path(html_path).parent / "assets" / "audio" / f"{audio_id}.mp3")
        if Path(audio_path).exists():
            dur = _sp.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "csv=p=0", audio_path],
                capture_output=True, text=True, timeout=30
            ).stdout.strip()
            if dur:
                html = re.sub(
                    rf'(id="{audio_id}"[^>]*data-duration=")[^"]*(")',
                    lambda m, d=dur: m.group(1) + f"{float(d):.3f}" + m.group(2),
                    html,
                )

    if dry_run:
        # Show diff
        import difflib
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            html.splitlines(keepends=True),
            fromfile=html_path,
            tofile=html_path + " (patched)",
        )
        return "".join(diff)
    else:
        with open(html_path, "w") as f:
            f.write(html)
        return f"Patched {html_path}"


# ---------------------------------------------------------------------------
# 6. Generate a human-readable timing report
# ---------------------------------------------------------------------------

def print_report(timings: list[dict], total_dur: float):
    """Print a formatted timing comparison report."""
    print()
    print("=" * 90)
    print("  TIMING CORRECTION REPORT")
    print("=" * 90)
    print(f"\n  Narration duration: {total_dur:.3f}s")
    print()
    print(f"  {'Scene':<22} {'Old Start':>10} {'Old Dur':>8} → {'New Start':>10} {'New Dur':>8}  {'Nar Start':>10} {'Nar End':>10}  {'Conf':>5}")
    print(f"  {'-'*21} {'-'*10} {'-'*8}   {'-'*10} {'-'*8}  {'-'*10} {'-'*10}  {'-'*5}")

    for t in timings:
        old_start = t["data_start"]
        old_dur = t["data_duration"]
        print(f"  {t['id']:<22} {old_start:>10.1f} {old_dur:>8.1f} → "
              f"{t['new_start']:>10.3f} {t['new_duration']:>8.3f}  "
              f"{t['nar_start']:>10.3f} {t['nar_end']:>10.3f}  "
              f"{t['confidence']:>4.0%}")

    print()
    print("  Scene text matching:")
    for t in timings:
        print(f"\n  [{t['id']}] conf={t['confidence']:.0%}")
        for line in t["text_lines"]:
            print(f"      {line[:80]}")
        if t["confidence"] < 0.3:
            print(f"      ⚠ LOW CONFIDENCE — check manually!")
    print()


# ---------------------------------------------------------------------------
# 7. Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="ASR-driven narration-to-text timing corrector for HyperFrames",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("project_dir", help="Path to project directory (contains index.html)")
    parser.add_argument("--narration", help="Path to narration audio (default: PROJECT/assets/audio/narration.mp3)")
    parser.add_argument("--asr-json", help="Use pre-computed ASR JSON instead of running ASR")
    parser.add_argument("--dry-run", action="store_true", help="Print report and diff, don't modify files")
    parser.add_argument("--html", help="Path to HTML file (default: PROJECT/index.html)")
    args = parser.parse_args()

    project = Path(args.project_dir)
    if not project.is_dir():
        print(f"Error: {project} is not a directory", file=sys.stderr)
        sys.exit(1)

    html_path = Path(args.html) if args.html else project / "index.html"
    if not html_path.exists():
        print(f"Error: {html_path} not found", file=sys.stderr)
        sys.exit(1)

    narration = Path(args.narration) if args.narration else project / "assets" / "audio" / "narration.mp3"
    if not narration.exists():
        print(f"Warning: {narration} not found, looking for alternatives…")
        # Try to find any mp3 in assets/audio/
        audio_dir = project / "assets" / "audio"
        mp3s = list(audio_dir.glob("*.mp3"))
        if mp3s:
            narration = mp3s[0]
            print(f"  Using {narration}")
        else:
            print(f"Error: no audio found in {audio_dir}", file=sys.stderr)
            sys.exit(1)

    print(f"\n  Project:  {project}")
    print(f"  HTML:     {html_path}")
    print(f"  Narration: {narration}")

    # Step 1: Get ASR result
    if args.asr_json:
        print(f"\n  Loading ASR from: {args.asr_json}")
        asr_result = load_asr(args.asr_json)
    else:
        asr_dir = str(project / ".sync-timings")
        asr_result = run_asr(str(narration), asr_dir)

    segments = asr_result.get("segments", [])
    total_dur = max(s["end"] for s in segments) if segments else 0
    print(f"  ASR segments: {len(segments)}, total: {total_dur:.3f}s")

    # Step 2: Parse HTML scenes
    scenes = parse_html_scenes(str(html_path))
    print(f"  HTML scenes: {len(scenes)}")
    if not scenes:
        print("Error: no text-clip scenes found in HTML", file=sys.stderr)
        sys.exit(1)

    # Step 3: Match
    print("\n  Matching scenes to ASR segments …")
    matched = match_scenes_to_segments(scenes, segments)

    # Check for low confidence matches
    low_conf = [m for m in matched if m["confidence"] < 0.3]
    if low_conf:
        print(f"  ⚠ {len(low_conf)} scene(s) have low matching confidence:")
        for m in low_conf:
            print(f"     [{m['id']}] \"{m['full_text'][:40]}…\" (conf={m['confidence']:.0%})")

    # Step 4: Compute corrected timings
    timings = compute_timings(matched, total_dur)

    # Step 5: Report
    print_report(timings, total_dur)

    # Step 6: Patch
    if not args.dry_run:
        result = patch_html(str(html_path), timings, dry_run=False)
        print(f"\n  ✓ {result}")
    else:
        diff = patch_html(str(html_path), timings, dry_run=True)
        print("\n  DRY RUN — changes not applied. Diff:")
        print(diff)

    # Summary
    total_shift = sum(abs(t["new_start"] - t["data_start"]) for t in timings)
    print(f"\n  Summary: {len(timings)} scenes corrected, "
          f"total start-time shift = {total_shift:.1f}s")
    print(f"  Old total duration: {max(t['data_start'] + t['data_duration'] for t in timings):.1f}s")
    print(f"  New total duration: {max(t['new_start'] + t['new_duration'] for t in timings):.1f}s")
    print(f"  Narration duration: {total_dur:.3f}s")
    if not args.dry_run:
        print(f"  HTML patched. Re-render to see the fix.")
    print()


if __name__ == "__main__":
    main()
