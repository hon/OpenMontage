"""User preferences and run history management.

OpenMontage 的经验系统：让 agent 跨项目记住用户偏好和历史教训。

两个数据源
----------
1. ``user_preferences.yaml`` (项目根目录) — 用户主动声明的偏好。
   Agent 在 preflight 阶段读取，在 proposal 阶段将偏好纳入决策。

2. ``run_history.yaml`` (项目根目录) — 每次项目完成后 agent 自动追加
   的运行记录，包括使用的工具、效果评价、经验教训。

Agent 集成协议
--------------
- **Preflight 阶段**: 调用 ``load_preferences()``，将偏好输出到 capability menu。
- **Proposal 阶段**: 调用 ``load_run_history()`` + ``summarize_recent_history()``，
  参考最近 N 条历史经验进行决策。
- **Compose 完成阶段**: 调用 ``append_run_entry()``，将本次运行的经验记录下来。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------

def get_project_root() -> Path:
    """Return the OpenMontage project root (parent of ``lib/``)."""
    return Path(__file__).resolve().parent.parent


def get_preferences_path() -> Path:
    """Return the absolute path to ``user_preferences.yaml``."""
    return get_project_root() / "user_preferences.yaml"


def get_history_path() -> Path:
    """Return the absolute path to ``run_history.yaml``."""
    return get_project_root() / "run_history.yaml"


# ---------------------------------------------------------------------------
# 偏好读写
# ---------------------------------------------------------------------------

def load_preferences() -> dict[str, Any]:
    """Load user preferences from ``user_preferences.yaml``.

    Returns an empty dict if the file doesn't exist or is empty.
    Agent 在 preflight 阶段调用此函数。
    """
    path = get_preferences_path()
    if not path.exists():
        return {}
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 历史记录读写
# ---------------------------------------------------------------------------

def load_run_history() -> dict[str, Any]:
    """Load run history from ``run_history.yaml``.

    Returns ``{"entries": []}`` if the file doesn't exist or is empty.
    Agent 在 proposal 阶段调用此函数，参考历史经验。
    """
    path = get_history_path()
    if not path.exists():
        return {"entries": []}
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict) and "entries" in data:
            return data
        return {"entries": []}
    except Exception:
        return {"entries": []}


def append_run_entry(entry: dict[str, Any]) -> None:
    """Append one run entry to ``run_history.yaml``.

    Agent 在 compose 完成／项目结束后调用此函数。

    Parameters
    ----------
    entry:
        结构化的运行记录，建议包含以下字段:

        .. code-block:: python

            {
                "project_id": "trading-two-pillars",
                "title": "交易的 two pillars 视频",
                "pipeline": "animated-explainer",
                "tts_provider": "kokoro",       # 实际使用的 TTS
                "tts_voice": "zh_female_warm",
                "tts_rating": "great",           # excellent / great / acceptable / poor
                "render_runtime": "remotion",    # 实际使用的合成引擎
                "render_success": True,
                "total_cost_usd": 0.0,
                "duration_seconds": 89,
                "notes": "Kokoro 中文效果很好，之后继续优先使用",
                "preferences_learned": {          # 从这次运行推断出的新偏好
                    "tts": {"preferred_provider": "kokoro"}
                },
            }
    """
    import yaml

    path = get_history_path()
    history = load_run_history()

    entry.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    history["entries"].append(entry)

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(history, f, allow_unicode=True, sort_keys=False)


# ---------------------------------------------------------------------------
# 查询辅助
# ---------------------------------------------------------------------------

def summarize_recent_history(
    history: dict[str, Any] | None = None,
    n: int = 5,
) -> list[dict[str, Any]]:
    """Return the N most recent run entries for agent reference.

    Agent 在 proposal 阶段调用此函数，快速了解最近项目的做法和效果。
    """
    if history is None:
        history = load_run_history()
    entries = history.get("entries", [])
    return entries[-n:]


def summarize_preferences(prefs: dict[str, Any] | None = None) -> str:
    """Return a human-readable summary of active user preferences.

    Agent 在 preflight 或 proposal 阶段调用，将偏好用自然语言表示。
    """
    if prefs is None:
        prefs = load_preferences()
    if not prefs:
        return "无用户偏好设置（全部使用 agent 默认决策）"

    lines: list[str] = []
    for category, values in prefs.items():
        if not isinstance(values, dict):
            continue
        active = {k: v for k, v in values.items() if v is not None}
        if active:
            items = ", ".join(f"{k}={v}" for k, v in active.items())
            lines.append(f"  [{category}] {items}")

    if not lines:
        return "无活跃偏好设置"

    return "用户偏好:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 便捷 getter
# ---------------------------------------------------------------------------

def get_preferred_tts(
    prefs: dict[str, Any] | None = None,
) -> tuple[Optional[str], Optional[str]]:
    """Return ``(preferred_provider, preferred_voice)`` from preferences."""
    if prefs is None:
        prefs = load_preferences()
    tts = prefs.get("tts", {})
    return tts.get("preferred_provider"), tts.get("preferred_voice")


def get_preferred_runtime(
    prefs: dict[str, Any] | None = None,
) -> Optional[str]:
    """Return preferred render runtime from preferences."""
    if prefs is None:
        prefs = load_preferences()
    render = prefs.get("render", {})
    return render.get("preferred_runtime")


def get_preferred_resolution(
    prefs: dict[str, Any] | None = None,
) -> str:
    """Return preferred resolution (default ``1920x1080``)."""
    if prefs is None:
        prefs = load_preferences()
    render = prefs.get("render", {})
    return str(render.get("preferred_resolution", "1920x1080"))


def get_default_budget_cap(
    prefs: dict[str, Any] | None = None,
) -> float:
    """Return default budget cap (default ``10.0``)."""
    if prefs is None:
        prefs = load_preferences()
    budget = prefs.get("budget", {})
    return float(budget.get("default_cap_usd", 10.0))
