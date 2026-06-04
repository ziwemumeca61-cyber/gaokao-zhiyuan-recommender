"""冲稳保位次法。

用考生位次与院校专业近年参考位次的比值 r = 考生位次 / 院校位次 分档：
  r > STABLE_HIGH  -> 冲（考生位次更靠后，需要冲一冲），上限 RUSH_MAX
  STABLE_LOW..HIGH -> 稳
  r < STABLE_LOW   -> 保（考生更有优势），下限 SAFE_MIN
区间外的候选视为不相关（太冒险或太浪费），返回 None。
"""

from __future__ import annotations

from ..models import TIER_RUSH, TIER_SAFE, TIER_STABLE

# 阈值常量（集中便于调参）
RUSH_MAX = 1.30      # r 超过此值，过于冒险，剔除
STABLE_HIGH = 1.08   # r 在 (STABLE_HIGH, RUSH_MAX] 为冲
STABLE_LOW = 0.90    # r 在 [STABLE_LOW, STABLE_HIGH] 为稳
SAFE_MIN = 0.55      # r 低于此值，过于浪费，剔除


def ratio(student_rank: int, ref_rank: int) -> float:
    if ref_rank <= 0:
        return 1.0
    return student_rank / ref_rank


def classify(student_rank: int, ref_rank: int) -> str | None:
    """返回 冲/稳/保，区间外返回 None。"""
    r = ratio(student_rank, ref_rank)
    if r > RUSH_MAX or r < SAFE_MIN:
        return None
    if r > STABLE_HIGH:
        return TIER_RUSH
    if r >= STABLE_LOW:
        return TIER_STABLE
    return TIER_SAFE
