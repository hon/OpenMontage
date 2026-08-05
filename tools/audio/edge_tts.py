"""Microsoft Edge online text-to-speech provider tool.

edge-tts is a free, unofficial client for Microsoft Edge's online TTS service.
No API key required. Supports 100+ languages including Mandarin Chinese.

Install: pip install edge-tts
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    RetryPolicy,
    ToolResult,
    ToolRuntime,
    ToolStability,
    ToolStatus,
    ToolTier,
)


class EdgeTTS(BaseTool):
    name = "edge_tts"
    version = "0.1.0"
    tier = ToolTier.VOICE
    capability = "tts"
    provider = "microsoft_edge"
    stability = ToolStability.PRODUCTION
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC
    runtime = ToolRuntime.API  # calls MS online service, but free + no key

    dependencies = ["pip:edge-tts"]
    install_instructions = (
        "Install Edge TTS:\n"
        "  pip install edge-tts\n"
        "No API key required."
    )
    agent_skills = ["text-to-speech"]

    capabilities = [
        "text_to_speech",
        "multilingual",
    ]
    supports = {
        "voice_cloning": False,
        "multilingual": True,
        "offline": False,
        "native_audio": True,
        "speed_control": True,
        "pitch_control": False,
    }
    best_for = [
        "free narration with no API key",
        "high-quality Chinese TTS",
        "quick prototyping without setup",
    ]
    not_good_for = [
        "offline workflows",
        "voice clone matching",
        "commercial use where ToS matters",
    ]

    # Language -> default voice mapping
    DEFAULT_VOICES = {
        "zh": "zh-CN-XiaoxiaoNeural",
        "en": "en-US-AriaNeural",
        "ja": "ja-JP-NanamiNeural",
        "ko": "ko-KR-SunHiNeural",
        "fr": "fr-FR-DeniseNeural",
        "de": "de-DE-KatjaNeural",
        "es": "es-ES-ElviraNeural",
        "it": "it-IT-ElsaNeural",
        "pt": "pt-BR-FranciscaNeural",
        "ru": "ru-RU-SvetlanaNeural",
    }

    input_schema = {
        "type": "object",
        "required": ["text"],
        "properties": {
            "text": {"type": "string"},
            "voice": {
                "type": "string",
                "description": "Edge TTS voice name. Run 'edge-tts --list-voices' to see all.",
                "default": "zh-CN-XiaoxiaoNeural",
            },
            "speed": {
                "type": "number",
                "description": "Speaking rate. 1.0 = normal, 0.5 = half speed, 2.0 = double.",
                "default": 1.0,
                "minimum": 0.25,
                "maximum": 2.0,
            },
            "volume": {
                "type": "number",
                "description": "Volume gain in dB. Positive = louder.",
                "default": 0.0,
            },
            "output_path": {"type": "string"},
        },
    }

    resource_profile = ResourceProfile(
        cpu_cores=1, ram_mb=128, vram_mb=0, disk_mb=50, network_required=True
    )
    retry_policy = RetryPolicy(max_retries=2, retryable_errors=["ConnectionError", "TimeoutError"])
    idempotency_key_fields = ["text", "voice", "speed"]
    side_effects = ["writes audio file to output_path"]
    user_visible_verification = ["Listen to generated audio for intelligibility"]

    def get_status(self) -> ToolStatus:
        if shutil.which("edge-tts"):
            return ToolStatus.AVAILABLE
        try:
            import edge_tts  # noqa: F401
            return ToolStatus.AVAILABLE
        except ImportError:
            return ToolStatus.UNAVAILABLE

    def estimate_cost(self, inputs: dict[str, Any]) -> float:
        return 0.0

    def _detect_language(self, text: str) -> str:
        """Simple heuristic to guess language from text."""
        # Check for Chinese characters
        for ch in text:
            if "\u4e00" <= ch <= "\u9fff":
                return "zh"
        # Check for hiragana/katakana (Japanese)
        for ch in text:
            if "\u3040" <= ch <= "\u309f" or "\u30a0" <= ch <= "\u30ff":
                return "ja"
        # Check for Hangul (Korean)
        for ch in text:
            if "\uac00" <= ch <= "\ud7af":
                return "ko"
        return "en"

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        if self.get_status() != ToolStatus.AVAILABLE:
            return ToolResult(
                success=False,
                error="Edge TTS not available. " + self.install_instructions,
            )

        start = time.time()
        try:
            result = self._generate(inputs)
        except Exception as exc:
            return ToolResult(success=False, error=f"Edge TTS generation failed: {exc}")

        result.duration_seconds = round(time.time() - start, 2)
        return result

    def _generate(self, inputs: dict[str, Any]) -> ToolResult:
        text = inputs["text"]
        output_path = Path(inputs.get("output_path", "tts_output.mp3"))
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Auto-detect voice if not provided
        voice = inputs.get("voice")
        if not voice:
            lang = self._detect_language(text)
            voice = self.DEFAULT_VOICES.get(lang, self.DEFAULT_VOICES["en"])

        speed = float(inputs.get("speed", 1.0))
        volume = float(inputs.get("volume", 0.0))

        cmd = [
            "edge-tts",
            "--voice", voice,
            "--text", text,
            "--write-media", str(output_path),
        ]

        # Edge TTS uses rate in percent: +50% = 1.5x speed
        if speed != 1.0:
            rate_pct = int((speed - 1.0) * 100)
            rate_str = f"{rate_pct:+d}%"
            cmd.extend(["--rate", rate_str])

        if volume != 0.0:
            vol_pct = int(volume * 100)
            vol_str = f"{vol_pct:+d}%"
            cmd.extend(["--volume", vol_str])

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if proc.returncode != 0:
            return ToolResult(
                success=False,
                error=f"Edge TTS failed (exit {proc.returncode}): {proc.stderr}",
            )
        if not output_path.exists():
            return ToolResult(
                success=False,
                error=f"Edge TTS output file missing: {output_path}",
            )

        return ToolResult(
            success=True,
            data={
                "provider": self.provider,
                "voice": voice,
                "speed": speed,
                "text_length": len(text),
                "output": str(output_path),
                "format": "mp3",
            },
            artifacts=[str(output_path)],
            model=voice,
        )
