"""专业科普知识：给任意专业补"简介 / 主修课程 / 就业去向 / 行业前景 / 适合谁"。

真实录取数据没有专业科普字段，这里按两级兜底保证每个专业都"看得懂"：
1) 专业名在精选知识库（data/major_catalog.CURATED_MAJORS）里精确或模糊命中；
2) 否则用其学科门类的通用模板。
"""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

from .models import Major

# 学科门类通用模板（命中不到精选专业时兜底）
CATEGORY_TEMPLATES: dict[str, dict] = {
    "工学": {
        "intro": "面向工程技术，强调把科学原理变成能用的产品与系统，动手与实践并重。",
        "core_courses": ["高等数学", "工程制图/程序设计", "专业基础课", "实验与课程设计"],
        "career_paths": ["研发/技术工程师", "生产与制造", "技术管理", "继续深造"],
        "industry_outlook": "工科岗位需求面广、就业稳定，与产业升级紧密相关。",
        "suits": "逻辑清晰、动手能力强、喜欢解决实际问题的人。",
    },
    "理学": {
        "intro": "研究自然界基本规律，重视数理基础与科学方法，偏理论与研究。",
        "core_courses": ["高等数学", "专业基础理论", "实验方法", "科研训练"],
        "career_paths": ["科研/教育", "数据与分析", "技术研发", "读研深造"],
        "industry_outlook": "基础学科，深造价值高，长期看好但本科直接对口岗位偏少。",
        "suits": "数理基础好、爱思考、对科学问题有好奇心的人。",
    },
    "医学": {
        "intro": "学习人体、疾病与诊疗，专业性强、培养周期长，社会需求稳定。",
        "core_courses": ["人体解剖学", "生理学", "病理学", "诊断学", "临床实习"],
        "career_paths": ["医院临床/医技", "公共卫生", "医药相关", "读研规培"],
        "industry_outlook": "健康需求长期增长，临床岗位多需深造与执业资格。",
        "suits": "责任心强、能吃苦、愿长期学习、关心他人健康的人。",
    },
    "农学": {
        "intro": "研究农业生产与生命科学应用，连接田间与实验室，强调实践。",
        "core_courses": ["生物学基础", "遗传育种", "栽培/养殖学", "田间实习"],
        "career_paths": ["农业技术/育种", "食品与生物", "农业管理", "深造科研"],
        "industry_outlook": "现代农业与生物育种受政策支持，特色方向前景好。",
        "suits": "热爱自然、踏实肯干、对生命科学感兴趣的人。",
    },
    "经济学": {
        "intro": "研究资源配置与经济规律，数理与财经结合，应用面广。",
        "core_courses": ["微观/宏观经济学", "计量经济学", "金融学", "统计学"],
        "career_paths": ["金融/银行/证券", "财经分析", "政府与研究机构", "企业经管"],
        "industry_outlook": "财经岗位竞争激烈，名校与量化能力是加分项。",
        "suits": "数感好、关注社会经济、逻辑与表达兼备的人。",
    },
    "管理学": {
        "intro": "研究组织如何高效运转，覆盖管理、财会、营销等，实用性强。",
        "core_courses": ["管理学", "会计学", "市场营销", "运营/财务管理"],
        "career_paths": ["企业管理/运营", "财务会计", "市场与人力", "考公考编"],
        "industry_outlook": "应用广、入门门槛适中，需结合行业经验形成竞争力。",
        "suits": "善沟通协调、条理性强、愿意与人和事打交道的人。",
    },
    "法学": {
        "intro": "学习法律规则与法律思维，培养依法分析与解决问题的能力。",
        "core_courses": ["法理学", "宪法/民法/刑法", "诉讼法", "案例与实务"],
        "career_paths": ["法院/检察院/律师", "企业法务", "公务员", "法律研究"],
        "industry_outlook": "需通过法考方能从业，名校与实务经验很关键。",
        "suits": "逻辑严谨、记忆与表达好、有正义感的人。",
    },
    "文学": {
        "intro": "学习语言文字与文学传播，重视阅读、写作与跨文化沟通。",
        "core_courses": ["语言学", "文学史", "写作", "传播/翻译"],
        "career_paths": ["教育/媒体", "文案与编辑", "外贸/涉外", "公务员"],
        "industry_outlook": "需'语言+第二技能'复合，内容行业有机会。",
        "suits": "文字功底好、爱阅读表达、细腻有人文情怀的人。",
    },
    "教育学": {
        "intro": "研究教育与人的发展，面向教学、教研与教育管理。",
        "core_courses": ["教育学原理", "教育心理学", "课程与教学论", "教育实习"],
        "career_paths": ["中小学/幼儿教师", "教研员", "教育机构", "教育行政"],
        "industry_outlook": "考编需求稳定，教育数字化带来新岗位。",
        "suits": "有爱心耐心、喜欢与人相处、乐于助人成长的人。",
    },
    "历史学": {
        "intro": "研究人类历史与文化遗产，重视史料分析与思辨。",
        "core_courses": ["中国/世界通史", "史学理论", "考古/文献", "专题研究"],
        "career_paths": ["教育/研究", "博物馆/档案", "文化传媒", "公务员"],
        "industry_outlook": "对口岗位偏少，深造与'历史+'复合更有出路。",
        "suits": "爱读书思考、记忆与分析力强、对历史文化有热情的人。",
    },
    "哲学": {
        "intro": "探讨世界、知识与价值的根本问题，训练深度思辨能力。",
        "core_courses": ["哲学导论", "中西哲学史", "逻辑学", "伦理学"],
        "career_paths": ["教育/研究", "文化出版", "公务员", "跨领域深造"],
        "industry_outlook": "就业面较窄，适合深造，思维能力是长期优势。",
        "suits": "爱思考、能坐冷板凳、对根本问题着迷的人。",
    },
    "艺术学": {
        "intro": "学习艺术创作与设计表达，重视审美、创意与动手实践。",
        "core_courses": ["艺术/设计基础", "专业创作", "软件/技法", "作品集"],
        "career_paths": ["设计/创意", "文化传媒", "教育培训", "自由职业"],
        "industry_outlook": "数字内容旺盛，需持续打磨作品与紧跟趋势。",
        "suits": "审美好、有创意、愿意持续打磨作品的人。",
    },
    "__default__": {
        "intro": "该专业的科普信息暂未收录，建议查阅目标院校的培养方案了解详情。",
        "core_courses": ["公共基础课", "专业核心课", "实践/实习环节"],
        "career_paths": ["对口行业就业", "考研深造", "考公考编"],
        "industry_outlook": "请结合院校实力与个人兴趣综合判断。",
        "suits": "对该领域有兴趣、愿意投入学习的人。",
    },
}


@lru_cache(maxsize=1)
def _curated() -> dict[str, dict]:
    """从 data/major_catalog 载入精选专业知识；失败则返回空。"""
    data_dir = Path(__file__).resolve().parents[2] / "data"
    if str(data_dir) not in sys.path:
        sys.path.insert(0, str(data_dir))
    try:
        import major_catalog  # noqa: PLC0415

        return {m["name"]: m for m in major_catalog.CURATED_MAJORS}
    except Exception:  # noqa: BLE001
        return {}


def _normalize(name: str) -> str:
    """规范化专业名：去掉括号注释与末尾的"类"，便于精确比对。"""
    s = name.strip()
    for sep in ("（", "("):
        if sep in s:
            s = s.split(sep)[0]
    s = s.strip()
    if len(s) > 2 and s.endswith("类"):
        s = s[:-1]
    return s


def _lookup(name: str, table: dict) -> dict | None:
    """在精选表里为专业名找最贴切条目；找不到返回 None。

    只接受精确名或"整段前缀"关系（如 物理学类→物理学、护理→护理学），且较短一方≥2字，
    取匹配最长者。**不做任意子串匹配**，避免「书法学→法学」「机械…自动化→自动化」之类误配。
    """
    if name in table:
        return table[name]
    n = _normalize(name)
    best_len, best = 0, None
    for cname, info in table.items():
        c = _normalize(cname)
        if not c:
            continue
        if n == c or (len(n) >= 2 and len(c) >= 2 and (n.startswith(c) or c.startswith(n))):
            if len(c) > best_len:
                best_len, best = len(c), info
    return best


def knowledge_for(name: str, category: str) -> dict:
    """返回某专业的科普字典（intro/core_courses/career_paths/industry_outlook/suits）。"""
    hit = _lookup(name, _curated())
    if hit is not None:
        return hit
    return CATEGORY_TEMPLATES.get(category, CATEGORY_TEMPLATES["__default__"])


def heat_for(name: str, category: str) -> float:
    """专业热度 0~100：精选专业用真实热度，其余给基准值 50（用于'热门推荐'排序）。"""
    hit = _lookup(name, _curated())
    if hit is not None:
        return float(hit.get("heat", 50))
    return 50.0


def detail_for(major: Major) -> dict:
    """合并专业自带字段与知识库兜底，返回用于展示的完整科普字典。"""
    k = knowledge_for(major.name, major.category)
    return {
        "intro": major.intro or k["intro"],
        "core_courses": major.core_courses or list(k["core_courses"]),
        "career_paths": major.career_paths or list(k["career_paths"]),
        "industry_outlook": major.industry_outlook or k["industry_outlook"],
        "suits": major.suits or k["suits"],
    }
