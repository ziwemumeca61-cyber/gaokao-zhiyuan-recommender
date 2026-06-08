"""品牌/贴牌配置：产品名、副标题、机构名、免责声明等可改，便于卖给不同机构。

读取仓库根目录的 branding.json（缺失或损坏时用内置默认值）。改这个文件即可贴牌，
无需改代码。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_DEFAULTS: dict[str, str] = {
    "app_title": "高考志愿小助手",
    "app_icon": "🎓",
    "subtitle": "分数不浪费，专业不踩坑，志愿填得明明白白 ✨",
    "org_name": "",  # 机构/代理商名称，留空则不显示
    "disclaimer": "结果仅供参考，正式填报请以各省考试院与院校招生章程为准。",
}


@lru_cache(maxsize=1)
def _brand() -> dict[str, str]:
    path = Path(__file__).resolve().parents[2] / "branding.json"
    data = dict(_DEFAULTS)
    if path.exists():
        try:
            data.update(json.loads(path.read_text(encoding="utf-8")))
        except Exception:  # noqa: BLE001
            pass
    return data


def get(key: str) -> str:
    return _brand().get(key, _DEFAULTS.get(key, ""))
