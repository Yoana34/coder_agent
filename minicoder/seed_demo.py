"""把 demo 场景文件复制到工作区，作为 agent 的任务输入。

demo/ 目录是仓库里保存的"任务场景模板"（故意带 bug）；
workspace/ 是 agent 的工作区（沙箱，gitignore）。运行前先 seed 一次。
"""

from __future__ import annotations

import os
import shutil

_DEMO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "demo")
DEMO_FILES = ["buggy_wordcount.py", "sample.txt"]


def seed_demo(workspace: str) -> list[str]:
    """把 demo 场景复制进工作区（已存在则不覆盖）。返回实际复制/已存在的文件列表。"""
    ws = os.path.abspath(workspace)
    os.makedirs(ws, exist_ok=True)
    seeded: list[str] = []
    for f in DEMO_FILES:
        src = os.path.join(_DEMO_DIR, f)
        dst = os.path.join(ws, f)
        if os.path.exists(dst):
            continue  # 不覆盖用户已放置/已修改的文件
        if os.path.exists(src):
            shutil.copyfile(src, dst)
        seeded.append(dst)
    return seeded
