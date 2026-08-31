"""CLI 入口（argparse）：接入 Agent 主循环，统一处理配置/中断/失败退出码。"""

from __future__ import annotations

import argparse
import os
from typing import Callable

from . import __version__
from .agent import Agent
from .config import Config, load_dotenv
from .errors import AgentLimitExceeded, ConfigError, LLMError
from .llm import DeepSeekClient
from .mock_demo import MOCK_DEMO_SCRIPT, MOCK_DEMO_TASK
from .mock_llm import MockLLM
from .seed_demo import seed_demo

# REPL 中退出对话的关键词
_EXIT_WORDS = {"退出", "exit", "quit", "/exit", "q"}

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
        "--workspace",
        default=None,
        help="agent 工作区目录（默认 <当前目录>/workspace）。所有文件读写与命令都限制在此目录内",
    )
    p.add_argument(
        "--seed-demo",
        action="store_true",
        help="把 demo 场景文件复制到工作区（真实 API 运行前可先执行一次）",
    )
    p.add_argument(
        "--mock",
        action="store_true",
        help="使用内置离线 mock（无需 API key）：自动 seed 工作区并演示一次'读→修→跑→总结'",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def _banner(cfg: Config, mock: bool, workspace: str) -> str:
    mode = "离线 mock（无 API 调用）" if mock else f"DeepSeek API ({cfg.model})"
    return (
        "\n"
        "==============================================\n"
        "  MiniCoder — 从零实现的编程智能体\n"
        f"  模式: {mode}\n"
        f"  工作区: {workspace}\n"
        "==============================================\n"
    )


def _build_client(cfg: Config, mock: bool):
    if mock:
        return MockLLM(MOCK_DEMO_SCRIPT)
    return DeepSeekClient(cfg)


def _repl(
    cfg: Config,
    agent: Agent,
    *,
    mock: bool,
    initial_task: str | None = None,
    get_input: Callable[[str], str] = input,
) -> int:
    """多轮对话主循环。返回退出码。

    - 首个任务来自 CLI 参数 / --mock 演示；随后进入"继续对话"循环。
    - 空行或退出词结束；Ctrl+C 干净中断。
    - mock 模式演示一次后自动退出（脚本用尽无后续）。
    """
    task = initial_task
    rc = EXIT_OK
    while True:
        if task is None:
            task = get_input("任务 > ").strip()
            if not task:
                print("[提示] 未输入任务，退出。")
                return rc
        try:
            agent.run(task)
            rc = EXIT_OK
        except AgentLimitExceeded as e:
            print(f"\n[未完成] {e}")
            rc = EXIT_FAILED
        except LLMError as e:
            print(f"\n[LLM 错误] {e}")
            rc = EXIT_LLM
        except KeyboardInterrupt:
            print("\n[已中断]")
            return EXIT_INTERRUPT

        if mock:
            break  # 离线演示只跑一轮
        try:
            follow = get_input(
                "\n继续对话：输入下一个任务；空行或 退出/exit 结束。\n任务 > "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not follow or follow.lower() in _EXIT_WORDS:
            break
        task = follow
    return rc


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

    # 工作区：默认 <当前目录>/workspace，自动创建；mock 或 --seed-demo 时注入 demo 场景
    workspace = os.path.abspath(args.workspace or "workspace")
    os.makedirs(workspace, exist_ok=True)
    if args.mock or args.seed_demo:
        seed_demo(workspace)

    print(_banner(cfg, args.mock, workspace))

    client = _build_client(cfg, args.mock)
    agent = Agent(cfg, client, echo=True, workspace=workspace)
    initial_task = args.task or (MOCK_DEMO_TASK if args.mock else None)
    return _repl(cfg, agent, mock=args.mock, initial_task=initial_task)


if __name__ == "__main__":
    raise SystemExit(main())
