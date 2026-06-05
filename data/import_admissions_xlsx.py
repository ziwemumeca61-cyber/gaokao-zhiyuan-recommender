"""把"全国高校在某省的专业录取分数"Excel 转换为系统标准三表，写入 data/real。

源表列：年份/院校名称/院校代码/科类/批次/专业/专业代码/所属专业组/专业备注/选科要求/
        录取人数/最低分数/最低位次/学校所在/学校性质/是否985/是否211
仅保留普通类（一段/二段）有效行。学科门类由专业名关键词派生（best-effort），兴趣码按
门类映射，热度/就业率用占位默认值（真实值缺失时不影响冲稳保主链路）。

用法：
    python data/import_admissions_xlsx.py <录取省份> <专业录取分数.xlsx> [--out data/real]
例：
    python data/import_admissions_xlsx.py 山东 山东专业录取分数.xlsx
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gaokao.data_schema import CATEGORY_RIASEC, DEFAULT_RIASEC  # noqa: E402

KEEP_BATCHES = ("普通类一段", "普通类二段", "本科批", "专科批")

# 学科门类关键词（按优先级匹配，靠前优先）
_CATEGORY_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("医学", ("临床医", "口腔医", "中医", "护理", "药学", "医学", "预防医", "康复",
              "麻醉", "影像", "检验", "卫生", "针灸", "中药")),
    ("教育学", ("教育", "师范", "学前", "小学教育", "体育教育", "特殊教育")),
    ("艺术学", ("音乐", "美术", "设计", "舞蹈", "表演", "戏剧", "影视", "动画",
                "艺术", "播音", "摄影", "书法", "雕塑", "绘画")),
    ("农学", ("农学", "园艺", "林学", "动物", "植物", "水产", "畜牧", "茶学", "园林",
              "农业", "种子", "草业")),
    ("经济学", ("经济", "金融", "财政", "税收", "国际贸易", "投资", "保险")),
    ("管理学", ("管理", "会计", "工商", "市场营销", "物流", "人力资源", "旅游",
                "电子商务", "财务", "审计", "行政")),
    ("法学", ("法学", "法律", "政治", "社会学", "公安", "侦查", "知识产权",
              "国际事务", "马克思")),
    ("文学", ("汉语", "中文", "英语", "日语", "德语", "法语", "俄语", "西班牙",
              "新闻", "传播", "广告", "编辑", "翻译", "文学", "语言", "外语")),
    ("历史学", ("历史", "考古", "文物")),
    ("哲学", ("哲学", "宗教", "逻辑")),
    ("理学", ("数学", "物理学", "化学", "生物科学", "地理科学", "地质", "天文",
              "统计学", "应用化学", "信息与计算", "海洋科学", "心理学", "科学")),
    ("工学", ("工程", "机械", "电气", "电子", "计算机", "软件", "通信", "自动化",
              "土木", "建筑", "材料", "能源", "化工", "车辆", "航空", "网络",
              "数据", "人工智能", "物联网", "测控", "仪器", "环境", "食品",
              "纺织", "矿", "冶金", "交通", "船舶", "技术", "智能")),
]


def _category(major_name: str) -> str:
    s = str(major_name or "")
    for cat, kws in _CATEGORY_RULES:
        if any(k in s for k in kws):
            return cat
    return "工学"  # 兜底（占多数的门类）


def _level(is985: str, is211: str) -> str:
    if str(is985).strip() == "是":
        return "985"
    if str(is211).strip() == "是":
        return "211"
    return "普通"


def _major_id(school_code: str, major: str, extra: str) -> str:
    h = hashlib.md5(f"{major}|{extra}".encode()).hexdigest()[:8]
    return f"{school_code}_{h}"


def _to_int(v):
    try:
        return int(float(str(v).strip()))
    except (TypeError, ValueError):
        return None


def convert(prov: str, src: Path) -> dict[str, list[dict]]:
    import openpyxl  # noqa: PLC0415

    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    ws = wb.active
    it = ws.iter_rows(values_only=True)
    h = list(next(it))
    c = {k: h.index(k) for k in (
        "年份", "院校名称", "院校代码", "科类", "批次", "专业", "选科要求",
        "录取人数", "最低分数", "最低位次", "学校所在", "是否985", "是否211")}

    schools: dict[str, dict] = {}
    majors: dict[str, dict] = {}
    adms: list[dict] = []
    skipped = 0
    for r in it:
        batch = str(r[c["批次"]] or "")
        subject = str(r[c["科类"]] or "")
        if subject != "综合" and "物理" not in subject and "历史" not in subject:
            skipped += 1
            continue
        if not any(b in batch for b in KEEP_BATCHES):
            skipped += 1
            continue
        score, rank = _to_int(r[c["最低分数"]]), _to_int(r[c["最低位次"]])
        year = _to_int(r[c["年份"]])
        code = str(r[c["院校代码"]] or "").strip()
        major = str(r[c["专业"]] or "").strip()
        if not code or not major or score is None or rank is None or year is None or rank <= 0:
            skipped += 1
            continue

        subj = "综合" if subject == "综合" else ("物理" if "物理" in subject else "历史")
        sel = str(r[c["选科要求"]] or "")
        if code not in schools:
            schools[code] = {
                "id": code, "name": str(r[c["院校名称"]] or "").strip(),
                "province": str(r[c["学校所在"]] or "").strip(),
                "city": str(r[c["学校所在"]] or "").strip(),
                "level": _level(r[c["是否985"]], r[c["是否211"]]),
                "type": "综合", "tags": "",
            }
        mid = _major_id(code, major, sel)
        if mid not in majors:
            cat = _category(major)
            majors[mid] = {
                "id": mid, "name": major, "category": cat, "school_id": code,
                "riasec_code": CATEGORY_RIASEC.get(cat, DEFAULT_RIASEC),
                "heat": 50.0, "employment_rate": 0.85,
                "intro": "", "core_courses": "", "career_paths": "",
                "industry_outlook": "", "suits": "",
            }
        adms.append({
            "school_id": code, "major_id": mid, "year": year, "province": prov,
            "subject_type": subj, "min_score": score, "min_rank": rank,
            "plan_count": _to_int(r[c["录取人数"]]) or 0,
        })
    wb.close()
    return {"schools": list(schools.values()), "majors": list(majors.values()),
            "admissions": adms, "_skipped": skipped}


def _write(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("province")
    ap.add_argument("src")
    ap.add_argument("--out", default="data/real")
    a = ap.parse_args(argv)

    data = convert(a.province, Path(a.src))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    _write(out / "schools.csv", data["schools"],
           ["id", "name", "province", "city", "level", "type", "tags"])
    _write(out / "majors.csv", data["majors"],
           ["id", "name", "category", "school_id", "riasec_code", "heat",
            "employment_rate", "intro", "core_courses", "career_paths",
            "industry_outlook", "suits"])
    _write(out / "admission_scores.csv", data["admissions"],
           ["school_id", "major_id", "year", "province", "subject_type",
            "min_score", "min_rank", "plan_count"])
    print(f"✅ {a.province}：院校 {len(data['schools'])}、专业 {len(data['majors'])}、"
          f"录取记录 {len(data['admissions'])}（跳过 {data['_skipped']} 行）-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
