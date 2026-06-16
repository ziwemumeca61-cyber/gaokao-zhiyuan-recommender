"""回测：用历史年份预测最近一年(2025)的录取线与录取概率，量化推荐准不准。

方法（留出法）：仅用 ≤2024 的记录按生产逻辑预测 2025，再与 2025 真实值对比：
- 位次线预测误差（相对误差中位数、±10%/±20% 命中、系统偏差）
- 录取概率十分箱校准（预测概率 ≈ 实际录取率 则校准良好）

核心逻辑见 gaokao.recommender.backtest；tests/test_backtest.py 用同一逻辑守门。
用法： python scripts/backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaokao.recommender.backtest import TEST_YEAR, run_backtest  # noqa: E402


def main() -> int:
    m = run_backtest()
    if "line_median_rel" not in m:
        print(f"样本不足（n={m.get('n_groups', 0)}），无法回测。")
        return 1
    print(f"== 回测：用 ≤{TEST_YEAR - 1} 预测 {TEST_YEAR}，样本 {m['n_groups']:,} 个(校,专,省,科) ==\n")
    print("【位次线预测误差】(预测参考位次 vs 实际最低位次)")
    print(f"  相对误差中位数(绝对值): {m['line_median_rel'] * 100:.1f}%")
    print(f"  落在 ±10% 内: {m['line_within10'] * 100:.0f}%   "
          f"±20% 内: {m['line_within20'] * 100:.0f}%")
    print(f"  系统性偏差(均值,>0偏保守/低估难度): {m['line_bias'] * 100:+.1f}%\n")
    print("【录取概率校准】(预测概率 区间 -> 实际录取率)")
    print("  预测概率档    样本    平均预测    实际录取率")
    for b, (cnt, avg_p, obs) in m["buckets"].items():
        print(f"   {b * 10:>3}-{b * 10 + 10:>3}%   {cnt:>6}   "
              f"{avg_p * 100:>7.1f}%   {obs * 100:>8.1f}%")
    print(f"\n  平均校准误差(越小越准): {m['calib_error'] * 100:.1f}%")
    print(f"  Brier 分数(越小越准): {m['brier']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
