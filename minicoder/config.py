"""配置加载：环境变量 + 可选 .env 文件 + CLI 覆盖。

设计决策：.env 解析器自行实现（简单的 KEY=VALUE 行解析），不引入 python-dotenv，
保持依赖最小、逻辑透明。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace

from .errors import ConfigError

# 环境变量名 -> (类型, 默认值)
_DEFAULTS: dict[str, tuple[type, object]] = {
    "DEEPSEEK_API_KEY": (str, ""),
    "MINICODER_MODEL": (str, "deepseek-chat"),
    "MINICODER_BASE_URL": (str, "https://api.deepseek.com"),
    "MINICODER_MAX_ITERATIONS": (int, 15),
    "MINICODER_API_TIMEOUT": (int, 120),
    "MINICODER_TOOL_OUTPUT_LIMIT": (int, 8000),
    "MINICODER_MAX_MESSAGES": (int, 30),
}


def load_dotenv(path: str = ".env") -> None:
    """读取 .env 中的 KEY=VALUE（不覆盖已存在的环境变量）。

    解析规则：忽略空行与 # 注释；值可带单/双引号；不支持导出语法与跨行。
    """
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # 去掉包裹的引号
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


def _env_or_default(name: str) -> object:
    """取环境变量；缺失时返回默认值。类型按 _DEFAULTS 转换，非法则报配置错误。"""
    type_, default = _DEFAULTS[name]
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    if type_ is int:
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"环境变量 {name} 必须是整数，当前值: {raw!r}")
    return raw


@dataclass(frozen=True)
class Config:
    api_key: str
    model: str
    base_url: str
    max_iterations: int
    api_timeout: int
    tool_output_limit: int
    max_messages: int

    @classmethod
    def from_env(cls, **cli_overrides) -> "Config":
        """从环境变量构造配置；cli_overrides 为 CLI 参数覆盖（None 则忽略）。"""
        values = {k: _env_or_default(k) for k in _DEFAULTS}
        cfg = cls(
            api_key=str(values["DEEPSEEK_API_KEY"]),
            model=str(values["MINICODER_MODEL"]),
            base_url=str(values["MINICODER_BASE_URL"]).rstrip("/"),
            max_iterations=int(values["MINICODER_MAX_ITERATIONS"]),
            api_timeout=int(values["MINICODER_API_TIMEOUT"]),
            tool_output_limit=int(values["MINICODER_TOOL_OUTPUT_LIMIT"]),
            max_messages=int(values["MINICODER_MAX_MESSAGES"]),
        )
        # CLI 覆盖（跳过 None）
        overrides = {k: v for k, v in cli_overrides.items() if v is not None}
        if overrides:
            cfg = replace(cfg, **overrides)
        return cfg

    def validate(self, mock: bool = False) -> None:
        """校验配置。mock 模式下无需 API key。"""
        if self.max_iterations < 1:
            raise ConfigError("max_iterations 必须 >= 1")
        if not self.base_url:
            raise ConfigError("MINICODER_BASE_URL 不能为空")
        if not mock and not self.api_key:
            raise ConfigError(
                "缺少 DEEPSEEK_API_KEY。请设置环境变量或在 .env 中配置，"
                "或使用 --mock 进行离线演示。"
            )
