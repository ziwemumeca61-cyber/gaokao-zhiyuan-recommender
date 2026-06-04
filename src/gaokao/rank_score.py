"""分数⇄位次换算（一分一段表）。

高考按省份分别划线，故分数与位次的换算必须按 (province, subject_type) 进行，
跨省不可比。本模块从该省该科类的历年录取数据聚合出单调的"分数→位次"曲线，
在对数位次空间做线性插值，支持双向换算。范围外按边界夹紧并提示。

与志愿推荐复用同一份录取数据，保证口径一致；按省份参数化，真实数据接入后
即可天然区分各省，无需改动调用方。
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from functools import lru_cache

from .data_loader import load_admissions


@dataclass
class Conversion:
    """一次换算结果。clamped 为 True 表示输入超出数据范围、取了边界估计。"""

    value: int
    clamped: bool


class ScoreRankTable:
    """某省某科类的分数↔位次对照表。scores 升序、log_ranks 随之非增。

    范围内做分段线性插值（忠实于一分一段）；范围外用对数位次的全局线性回归外推
    （log10(rank) = a + b·score），并把结果标记为 clamped=True 表示"超出实测、估算"。
    """

    def __init__(self, scores: list[int], ranks: list[int]) -> None:
        self.scores = scores
        self.ranks = ranks
        self._log_ranks = [math.log10(r) for r in ranks]
        self._a, self._b = _linfit(scores, self._log_ranks)

    @property
    def score_min(self) -> int:
        return self.scores[0]

    @property
    def score_max(self) -> int:
        return self.scores[-1]

    @property
    def rank_best(self) -> int:
        return self.ranks[-1]   # 分数最高处位次最小

    @property
    def rank_worst(self) -> int:
        return self.ranks[0]

    def points(self) -> list[tuple[int, int]]:
        """返回 (分数, 位次) 列表，便于画曲线。"""
        return list(zip(self.scores, self.ranks))

    def rank_for_score(self, score: float) -> Conversion:
        if score < self.score_min or score > self.score_max:
            log_r = self._a + self._b * score
            return Conversion(value=int(round(10 ** log_r)), clamped=True)
        log_r = _interp(self.scores, self._log_ranks, score)
        return Conversion(value=int(round(10 ** log_r)), clamped=False)

    def score_for_rank(self, rank: int) -> Conversion:
        log_r = math.log10(max(rank, 1))
        if rank < self.rank_best or rank > self.rank_worst:
            score = (log_r - self._a) / self._b if self._b else self.scores[-1]
            return Conversion(value=int(round(score)), clamped=True)
        # 位次随分数非增；以 log 位次升序（即分数降序）建视图做插值
        log_desc = self._log_ranks[::-1]
        score_desc = self.scores[::-1]
        return Conversion(value=int(round(_interp(log_desc, score_desc, log_r))),
                          clamped=False)


def _linfit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """最小二乘拟合 y = a + b·x，返回 (a, b)。点数不足时 b=0。"""
    n = len(xs)
    if n < 2:
        return (ys[0] if ys else 0.0, 0.0)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return (my, 0.0)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    a = my - b * mx
    return (a, b)


def _interp(xs: list[float], ys: list[float], x: float) -> float:
    """在升序 xs 上对 (xs, ys) 做线性插值；x 越界时取端点。"""
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_left(xs, x)
    x0, x1 = xs[i - 1], xs[i]
    y0, y1 = ys[i - 1], ys[i]
    if x1 == x0:
        return y0
    t = (x - x0) / (x1 - x0)
    return y0 + t * (y1 - y0)


@lru_cache(maxsize=None)
def _build_cached(province: str, subject_type: str, data_dir: str | None) -> ScoreRankTable | None:
    pairs: dict[int, list[int]] = {}
    for rec in load_admissions(data_dir):
        if rec.province == province and rec.subject_type == subject_type:
            pairs.setdefault(rec.min_score, []).append(rec.min_rank)
    if len(pairs) < 2:
        return None

    # 每个分数取位次的几何平均（log 空间均值），再按分数升序、位次单调清洗
    scores = sorted(pairs)
    ranks: list[int] = []
    for s in scores:
        logs = [math.log10(max(r, 1)) for r in pairs[s]]
        ranks.append(int(round(10 ** (sum(logs) / len(logs)))))
    # 分数升序时位次应非增；修掉因聚合产生的个别逆序
    for i in range(1, len(ranks)):
        if ranks[i] > ranks[i - 1]:
            ranks[i] = ranks[i - 1]
    return ScoreRankTable(scores, ranks)


def build_table(
    province: str, subject_type: str, data_dir: str | None = None
) -> ScoreRankTable | None:
    """构建某省某科类的一分一段表；数据不足时返回 None。"""
    return _build_cached(province, subject_type, data_dir)
