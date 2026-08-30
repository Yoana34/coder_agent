"""CLI 入口（argparse）：接入 Agent 主循环，统一处理配置/中断/失败退出码。"""

from __future__ import annotations

import argparse
import os

from . import __version__
from .agent import Agent
from .config import Config, load_dotenv
from .errors import AgentLimitExceeded, ConfigError, LLMError
from .llm import DeepSeekClient
from .mock_demo import MOCK_DEMO_SCRIPT, MOCK_DEMO_TASK
from .mock_llm import MockLLM

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_CONFIG = 2
EXIT_LLM = 3
EXIT_INTERRUPT = 130


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="minicoder",
        description="从零实现的编程智能体：让 LLM 自主读写文件、执行命令完成编程任务。",
    )
    p.add_argument("task", nargs="?", default=None, help="编程任务描述（缺省则交互式输入）")
    p.add_argument("--model", default=None, help="模型名（覆盖 MINICODER_MODEL）")
    p.add_argument("--max-iterations", type=int, default=None, help="最大迭代轮数（默认 15）")
    p.add_argument("--cwd", default=None, help="切换工作目录后再执行（默认当前目录）")
    p.add_argument(
        "--mock",
        action="store_true",
        help="使用内置离线 mock（无需 API key）：演示一次'读→修→跑→总结'完整闭环",
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


def _build_client(cfg: Config, mock: bool):
    if mock:
        return MockLLM(MOCK_DEMO_SCRIPT)
    return DeepSeekClient(cfg)


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
        return EXIT_CONFIG

    if args.cwd:
        os.chdir(args.cwd)

    print(_banner(cfg, args.mock))
    task = args.task or (MOCK_DEMO_TASK if args.mock else None)
    if not task:
        task = input("任务 > ").strip()
    if not task:
        print("[提示] 未输入任务，退出。")
        return EXIT_OK

    client = _build_client(cfg, args.mock)
    agent = Agent(cfg, client, echo=True)
    try:
        agent.run(task)
    except AgentLimitExceeded as e:
        print(f"\n[未完成] {e}")
        return EXIT_FAILED
    except LLMError as e:
        print(f"\n[LLM 错误] {e}")
        return EXIT_LLM
    except KeyboardInterrupt:
        print("\n[已中断]")
        return EXIT_INTERRUPT
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
