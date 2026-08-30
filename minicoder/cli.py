"""CLI 入口（argparse）。Step 1 提供骨架与配置校验；后续步骤接入 agent 主循环。"""

from __future__ import annotations

import argparse

from . import __version__
from .config import Config, load_dotenv
from .errors import ConfigError


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="minicoder",
        description="从零实现的编程智能体：让 LLM 自主读写文件、执行命令完成编程任务。",
    )
    p.add_argument("task", nargs="?", default=None, help="编程任务描述（缺省则交互式输入）")
    p.add_argument("--model", default=None, help="模型名（覆盖 MINICODER_MODEL）")
    p.add_argument("--max-iterations", type=int, default=None, help="最大迭代轮数（默认 15）")
    p.add_argument(
        "--mock",
        action="store_true",
        help="使用内置离线 mock LLM（无需 API key，用于演示与测试）",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _banner(cfg: Config, mock: bool) -> str:
    mode = "离线 mock（无 API 调用）" if mock else f"DeepSeek API ({cfg.model})"
    return (
        "\n"
        "==============================================\n"
        "  MiniCoder — 从零实现的编程智能体\n"
        f"  模式: {mode}\n"
        "==============================================\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    # 读取 .env（若存在）再构造配置，CLI 参数优先
    load_dotenv()
    try:
        cfg = Config.from_env(
            model=args.model,
            max_iterations=args.max_iterations,
        )
        cfg.validate(mock=args.mock)
    except ConfigError as e:
        print(f"[错误] {e}")
        return 2

    print(_banner(cfg, args.mock))
    task = args.task
    if not task:
        task = input("任务 > ").strip()
    if not task:
        print("[提示] 未输入任务，退出。")
        return 0

    # TODO(Step 4/6): 创建 Agent 并运行主循环
    print(f"[待实现] 已收到任务：{task}")
    print("[待实现] 主循环将在后续步骤接入。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
