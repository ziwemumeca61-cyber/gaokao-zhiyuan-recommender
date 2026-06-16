"""回测：用历史年份预测最近一年(2025)的录取线与录取概率，量化推荐准不准。

方法（留出法 / hold-out）：
- 对每个 (院校,专业,省,科类)，仅用 ≤2024 的记录按生产逻辑(history.aggregate)算出
  "参考位次"与波动，作为对 2025 的预测；再与 2025 真实最低位次对比。
- 位次预测误差：相对误差的中位数、落在 ±10%/±20% 内的比例。
- 概率校准：对一批"考生位次"用 ml_model 给出的录取概率，与"该位次是否真的过了
  2025 实际线"对比，按概率分箱看预测概率≈实际录取率（校准良好则两者接近）。

用法： python scripts/backtest.py
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaokao.data_loader import load_admissions  # noqa: E402
from gaokao.recommender import ml_model  # noqa: E402
from gaokao.recommender.history import aggregate  # noqa: E402

TEST_YEAR = 2025


def main() -> int:
    recs = load_admissions()
    groups: dict[tuple, dict[int, object]] = defaultdict(dict)
    for r in recs:
        groups[(r.school_id, r.major_id, r.province, r.subject_type)][r.year] = r

    rel_errs: list[float] = []
    calib: list[tuple[float, int]] = []  # (预测概率, 是否真的录取)
    n_back = 0

    for (sid, mid, prov, subj), by_year in groups.items():
        actual = by_year.get(TEST_YEAR)
        prior = [rec for y, rec in by_year.items() if y < TEST_YEAR]
        if actual is None or actual.min_rank <= 0 or len(prior) < 2:
            continue
        # 用生产逻辑对"仅历史年份"聚合，得到对 TEST_YEAR 的预测
        stat = aggregate(prior, prov, subj).get((sid, mid))
        if stat is None or stat.ref_rank <= 0:
            continue
        n_back += 1

        # 1) 位次预测误差（含招生计划修正后的投影参考位次，与推荐口径一致）
        pred = ml_model._proj_ref(stat.ref_rank, stat.plan_ratio)
        rel_errs.append((pred - actual.min_rank) / actual.min_rank)

        # 2) 概率校准：构造一批考生位次，看预测概率 vs 实际是否过线
        for factor in (0.55, 0.7, 0.85, 1.0, 1.2, 1.5, 1.9):
            cand_rank = max(1, round(stat.ref_rank * factor))
            prob = ml_model.predict_interval(
                cand_rank, stat.ref_rank, trend=stat.trend, rank_cv=stat.rank_cv,
                years=stat.years, plan=stat.total_plan, plan_ratio=stat.plan_ratio)[0]
            admitted = 1 if cand_rank <= actual.min_rank else 0  # 位次≤实际线=过线
            calib.append((prob, admitted))

    # ---- 位次预测误差 ----
    rel_errs.sort()
    n = len(rel_errs)
    abs_errs = sorted(abs(e) for e in rel_errs)
    med = abs_errs[n // 2]
    within10 = sum(1 for e in abs_errs if e <= 0.10) / n
    within20 = sum(1 for e in abs_errs if e <= 0.20) / n
    bias = sum(rel_errs) / n
    print(f"== 回测：用 ≤{TEST_YEAR - 1} 预测 {TEST_YEAR}，样本 {n_back:,} 个(校,专,省,科) ==\n")
    print("【位次线预测误差】(预测参考位次 vs 实际最低位次)")
    print(f"  相对误差中位数(绝对值): {med * 100:.1f}%")
    print(f"  落在 ±10% 内: {within10 * 100:.0f}%   ±20% 内: {within20 * 100:.0f}%")
    print(f"  系统性偏差(均值,>0偏保守/低估难度): {bias * 100:+.1f}%\n")

    # ---- 概率校准（十分箱）----
    print("【录取概率校准】(预测概率 区间 -> 实际录取率)")
    calib.sort()
    buckets: dict[int, list[tuple[float, int]]] = defaultdict(list)
    for p, a in calib:
        buckets[min(9, int(p * 10))].append((p, a))
    print("  预测概率档    样本    平均预测    实际录取率")
    tot_gap = 0.0
    for b in range(10):
        items = buckets.get(b, [])
        if not items:
            continue
        avg_p = sum(p for p, _ in items) / len(items)
        obs = sum(a for _, a in items) / len(items)
        tot_gap += abs(avg_p - obs) * len(items)
        print(f"   {b * 10:>3}-{b * 10 + 10:>3}%   {len(items):>6}   "
              f"{avg_p * 100:>7.1f}%   {obs * 100:>8.1f}%")
    print(f"\n  平均校准误差(越小越准): {tot_gap / len(calib) * 100:.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
