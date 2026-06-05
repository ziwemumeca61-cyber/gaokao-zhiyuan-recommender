"""测试统一固定到仓库内的确定性模拟数据。

本地可能存在 data/real（导入的真实数据，gitignore），算法测试需要确定性的模拟数据，
因此在测试会话中把 GAOKAO_DATA_DIR 指向 data/（模拟），不受 data/real 影响。
"""

import os
from pathlib import Path

_MOCK = Path(__file__).resolve().parents[1] / "data"
os.environ["GAOKAO_DATA_DIR"] = str(_MOCK)
