"""把购买的"一分一段"Excel 转换为 data/segments 种子 CSV。

适配列：年份 / 科类 / 批次 / 控制线(分) / 分数(分) / 本段人数(人) / 累计人数(人) / ...
（分数列支持区间如 "693-750"，取下界作为该累计位次对应的分数）。
排除艺术/体育等非普通类批次。科类自动归一为 物理 / 历史 / 综合。

用法：
    python data/import_segments_xlsx.py <省份> <文件1.xlsx> [文件2.xlsx ...]
例：
    python data/import_segments_xlsx.py 山东 a.xlsx b.xlsx
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

SEG_DIR = Path(__file__).resolve().parent / "segments"
_ART = ("艺术", "美术", "音乐", "舞蹈", "体育", "戏曲", "编导", "播音", "表演", "书法")


def _norm_subject(raw: str) -> str:
    s = str(raw or "")
    if "物理" in s:
        return "物理"
    if "历史" in s:
        return "历史"
    return "综合"


def _parse_score(raw) -> int | None:
    m = re.match(r"^\s*(\d+)", str(raw or ""))
    return int(m.group(1)) if m else None


def _parse_int(raw) -> int | None:
    try:
        return int(float(str(raw).strip()))
    except (TypeError, ValueError):
        return None


def load_xlsx(path: Path) -> dict[tuple[str, str], dict[int, int]]:
    """返回 {(年份, 科类): {分数: 累计位次}}。"""
    import openpyxl  # noqa: PLC0415

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    h = list(rows[0])
    col = {k: h.index(k) for k in ("年份", "科类", "批次", "分数(分)", "累计人数(人)")}

    out: dict[tuple[str, str], dict[int, int]] = {}
    for r in rows[1:]:
        batch = str(r[col["批次"]] or "")
        if any(a in batch for a in _ART):
            continue
        year = str(r[col["年份"]] or "").strip()
        subject = _norm_subject(r[col["科类"]])
        score = _parse_score(r[col["分数(分)"]])
        rank = _parse_int(r[col["累计人数(人)"]])
        if not year or score is None or rank is None or rank <= 0:
            continue
        out.setdefault((year, subject), {})[score] = rank
    wb.close()
    return out


def write_segments(province: str, data: dict[tuple[str, str], dict[int, int]]) -> list[str]:
    SEG_DIR.mkdir(parents=True, exist_ok=True)
    written = []
    for (year, subject), score_rank in data.items():
        pairs = sorted(score_rank.items())  # 按分数升序
        ranks = [r for _, r in pairs]
        # 分数升序时位次应非增；修掉个别逆序
        for i in range(1, len(ranks)):
            if ranks[i] > ranks[i - 1]:
                ranks[i] = ranks[i - 1]
        key = f"{province}_{subject}_{year}"
        path = SEG_DIR / f"{key}.csv"
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["score", "rank"])
            for (s, _), r in zip(pairs, ranks):
                w.writerow([s, r])
        written.append(f"{key}.csv（{len(pairs)} 段）")
    return written


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    province, files = argv[0], argv[1:]
    merged: dict[tuple[str, str], dict[int, int]] = {}
    for fp in files:
        for key, sr in load_xlsx(Path(fp)).items():
            merged.setdefault(key, {}).update(sr)
    written = write_segments(province, merged)
    print(f"✅ {province}：已写入 {len(written)} 份种子")
    for w in sorted(written):
        print("  -", w)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
