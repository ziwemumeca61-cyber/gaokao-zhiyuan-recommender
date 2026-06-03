"""生成模拟数据：schools.csv / majors.csv / admission_scores.csv。

数据是确定性的（固定随机种子），结构对齐真实数据，便于日后替换为真实来源。
用法：  python data/generate_mock_data.py
"""

from __future__ import annotations

import csv
import math
import random
from pathlib import Path

from major_catalog import CATEGORY_SUBJECT, CURATED_MAJORS

SEED = 20260603
DATA_DIR = Path(__file__).resolve().parent
# 考生来源省份（生成录取记录的维度）
PROVINCES = ["北京", "广东", "江苏", "四川", "湖南", "河南"]
YEARS = [2023, 2024, 2025]

# 院校名称素材：(城市, 省份, 名称, 层次, 类型)
SCHOOL_SEEDS = [
    ("北京", "北京", "清华大学", "985", "综合"),
    ("北京", "北京", "北京大学", "985", "综合"),
    ("北京", "北京", "北京航空航天大学", "985", "理工"),
    ("北京", "北京", "北京理工大学", "985", "理工"),
    ("北京", "北京", "北京师范大学", "985", "师范"),
    ("北京", "北京", "中国人民大学", "985", "综合"),
    ("上海", "上海", "复旦大学", "985", "综合"),
    ("上海", "上海", "上海交通大学", "985", "综合"),
    ("上海", "上海", "同济大学", "985", "理工"),
    ("上海", "上海", "华东师范大学", "985", "师范"),
    ("上海", "上海", "上海财经大学", "211", "财经"),
    ("广州", "广东", "中山大学", "985", "综合"),
    ("广州", "广东", "华南理工大学", "985", "理工"),
    ("深圳", "广东", "深圳大学", "普通", "综合"),
    ("南京", "江苏", "南京大学", "985", "综合"),
    ("南京", "江苏", "东南大学", "985", "理工"),
    ("南京", "江苏", "南京航空航天大学", "211", "理工"),
    ("南京", "江苏", "南京师范大学", "211", "师范"),
    ("成都", "四川", "四川大学", "985", "综合"),
    ("成都", "四川", "电子科技大学", "985", "理工"),
    ("成都", "四川", "西南财经大学", "211", "财经"),
    ("长沙", "湖南", "中南大学", "985", "综合"),
    ("长沙", "湖南", "湖南大学", "985", "综合"),
    ("长沙", "湖南", "湖南师范大学", "211", "师范"),
    ("武汉", "湖北", "武汉大学", "985", "综合"),
    ("武汉", "湖北", "华中科技大学", "985", "理工"),
    ("武汉", "湖北", "华中师范大学", "211", "师范"),
    ("西安", "陕西", "西安交通大学", "985", "综合"),
    ("西安", "陕西", "西北工业大学", "985", "理工"),
    ("西安", "陕西", "西安电子科技大学", "211", "理工"),
    ("哈尔滨", "黑龙江", "哈尔滨工业大学", "985", "理工"),
    ("杭州", "浙江", "浙江大学", "985", "综合"),
    ("合肥", "安徽", "中国科学技术大学", "985", "理工"),
    ("天津", "天津", "天津大学", "985", "理工"),
    ("天津", "天津", "南开大学", "985", "综合"),
    ("济南", "山东", "山东大学", "985", "综合"),
    ("重庆", "重庆", "重庆大学", "985", "综合"),
    ("郑州", "河南", "郑州大学", "211", "综合"),
    ("兰州", "甘肃", "兰州大学", "985", "综合"),
    ("大连", "辽宁", "大连理工大学", "985", "理工"),
]

# 用于扩展到约 100 所院校的名称模板
CITY_POOL = [
    ("石家庄", "河北"), ("太原", "山西"), ("南昌", "江西"), ("福州", "福建"),
    ("昆明", "云南"), ("贵阳", "贵州"), ("南宁", "广西"), ("沈阳", "辽宁"),
    ("长春", "吉林"), ("青岛", "山东"), ("苏州", "江苏"), ("宁波", "浙江"),
    ("厦门", "福建"), ("无锡", "江苏"), ("徐州", "江苏"),
]
NAME_PREFIX = ["", "", ""]  # 占位
TYPE_SUFFIX = {
    "综合": "大学", "理工": "理工大学", "师范": "师范大学",
    "财经": "财经大学", "农林": "农业大学", "医科": "医科大学",
}

# 院校层次 -> 录取最低位次基准区间（数字越小越难）
LEVEL_RANK_BASE = {
    "985": (800, 12000),
    "211": (8000, 45000),
    "双一流": (20000, 70000),
    "普通": (40000, 180000),
}

# 门类 -> 该门类下补充的通用专业名（用于丰富专业池）
EXTRA_MAJORS = {
    "工学": ["材料科学与工程", "能源与动力工程", "环境工程", "生物医学工程", "测控技术与仪器"],
    "理学": ["应用物理学", "信息与计算科学", "地理科学", "环境科学"],
    "经济学": ["国际经济与贸易", "财政学", "保险学"],
    "管理学": ["市场营销", "人力资源管理", "物流管理", "信息管理与信息系统"],
    "文学": ["广告学", "汉语国际教育"],
    "法学": ["社会学", "政治学与行政学"],
    "医学": ["预防医学", "药学", "中医学"],
    "农学": ["园艺", "动物科学", "植物保护"],
    "教育学": ["体育教育"],
    "艺术学": ["环境设计", "数字媒体艺术", "音乐学"],
}


def _rank_to_score(rank: int) -> int:
    """位次 -> 分数的单调映射（仅用于模拟，省内可比）。"""
    score = 720 - 32 * math.log10(max(rank, 10))
    return int(max(380, min(710, round(score))))


def build_schools(rng: random.Random) -> list[dict]:
    schools: list[dict] = []
    for i, (city, prov, name, level, stype) in enumerate(SCHOOL_SEEDS, start=1):
        schools.append({
            "id": f"S{i:03d}", "name": name, "province": prov, "city": city,
            "level": level, "type": stype,
            "tags": "|".join(_school_tags(level, stype)),
        })
    # 扩展到约 100 所（生成地方院校）
    idx = len(schools) + 1
    fillers = ["科技", "工程", "财经", "师范", "理工", "医科", "工商"]
    while len(schools) < 100:
        city, prov = rng.choice(CITY_POOL)
        stype = rng.choice(["综合", "理工", "师范", "财经", "医科"])
        level = rng.choices(["211", "双一流", "普通"], weights=[1, 2, 5])[0]
        kw = rng.choice(fillers)
        name = f"{city}{kw}学院" if level == "普通" else f"{prov}{kw}大学"
        schools.append({
            "id": f"S{idx:03d}", "name": name, "province": prov, "city": city,
            "level": level, "type": stype,
            "tags": "|".join(_school_tags(level, stype)),
        })
        idx += 1
    return schools


def _school_tags(level: str, stype: str) -> list[str]:
    tags = [level, stype]
    if level == "985":
        tags.append("双一流")
    return tags


def _master_major_pool() -> list[dict]:
    """精选专业 + 门类通用专业（带模板科普），作为分配给院校的母池。"""
    pool = [dict(m) for m in CURATED_MAJORS]
    known = {m["name"] for m in pool}
    for category, names in EXTRA_MAJORS.items():
        for name in names:
            if name in known:
                continue
            pool.append(_template_major(name, category))
    return pool


def _template_major(name: str, category: str) -> dict:
    """为没有精选文案的专业生成门类通用科普，保证'看得懂'。"""
    return {
        "name": name, "category": category, "riasec_code": _category_riasec(category),
        "heat": 45, "employ": 0.8,
        "intro": f"{name}属于{category}门类，系统学习该领域的基础理论与专业技能。",
        "core_courses": [f"{category}基础", "专业核心课", "实践与实验", "前沿专题"],
        "career_paths": [f"{category}相关技术岗", "行业研发/管理", "深造读研", "考公考编"],
        "industry_outlook": f"{category}门类应用面较广，结合个人兴趣与实习可形成竞争力。",
        "suits": f"对{category}领域有兴趣、愿意系统学习的人。",
    }


def _category_riasec(category: str) -> str:
    table = {
        "工学": "RI", "理学": "IR", "医学": "IS", "农学": "RI",
        "经济学": "IE", "管理学": "EC", "法学": "SE", "文学": "AS",
        "教育学": "SI", "历史学": "AI", "哲学": "AI", "艺术学": "AE",
    }
    return table.get(category, "IC")


def build_majors(schools: list[dict], rng: random.Random) -> list[dict]:
    """为每所院校分配若干专业，目标总量约 600。"""
    pool = _master_major_pool()
    majors: list[dict] = []
    for school in schools:
        # 综合类院校专业多，专科特色院校偏向相关门类
        n = rng.randint(5, 8)
        chosen = rng.sample(pool, k=min(n, len(pool)))
        for j, m in enumerate(chosen, start=1):
            mid = f"M{school['id'][1:]}{j:02d}"
            # 同一专业在不同院校的热度/就业率略有浮动
            heat = max(20, min(100, m["heat"] + rng.randint(-6, 6)))
            employ = round(min(0.99, max(0.6, m["employ"] + rng.uniform(-0.05, 0.05))), 3)
            majors.append({
                "id": mid, "name": m["name"], "category": m["category"],
                "school_id": school["id"], "riasec_code": m["riasec_code"],
                "heat": heat, "employment_rate": employ,
                "intro": m["intro"],
                "core_courses": "|".join(m["core_courses"]),
                "career_paths": "|".join(m["career_paths"]),
                "industry_outlook": m["industry_outlook"],
                "suits": m["suits"],
            })
    return majors


def _subject_types(category: str) -> list[str]:
    s = CATEGORY_SUBJECT.get(category, "物理")
    return ["物理", "历史"] if s == "兼报" else [s]


def build_admissions(
    schools: list[dict], majors: list[dict], rng: random.Random
) -> list[dict]:
    school_by_id = {s["id"]: s for s in schools}
    records: list[dict] = []
    for m in majors:
        school = school_by_id[m["school_id"]]
        lo, hi = LEVEL_RANK_BASE[school["level"]]
        # 热度越高 -> 越靠近区间下沿（更难）
        heat_factor = 1.0 - (m["heat"] - 20) / 100  # heat 20->1.0, 100->0.2
        base_rank = lo + (hi - lo) * heat_factor
        for prov in PROVINCES:
            prov_factor = 0.7 if prov == school["province"] else rng.uniform(0.9, 1.4)
            for subj in _subject_types(m["category"]):
                for year in YEARS:
                    year_noise = rng.uniform(0.92, 1.08)
                    rank = int(max(50, base_rank * prov_factor * year_noise))
                    records.append({
                        "school_id": school["id"], "major_id": m["id"],
                        "year": year, "province": prov, "subject_type": subj,
                        "min_score": _rank_to_score(rank), "min_rank": rank,
                        "plan_count": rng.randint(2, 30),
                    })
    return records


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    rng = random.Random(SEED)
    schools = build_schools(rng)
    majors = build_majors(schools, rng)
    admissions = build_admissions(schools, majors, rng)

    _write_csv(DATA_DIR / "schools.csv", schools,
               ["id", "name", "province", "city", "level", "type", "tags"])
    _write_csv(DATA_DIR / "majors.csv", majors,
               ["id", "name", "category", "school_id", "riasec_code", "heat",
                "employment_rate", "intro", "core_courses", "career_paths",
                "industry_outlook", "suits"])
    _write_csv(DATA_DIR / "admission_scores.csv", admissions,
               ["school_id", "major_id", "year", "province", "subject_type",
                "min_score", "min_rank", "plan_count"])

    print(f"已生成 {len(schools)} 所院校、{len(majors)} 个专业、"
          f"{len(admissions)} 条录取记录 -> {DATA_DIR}")


if __name__ == "__main__":
    main()
