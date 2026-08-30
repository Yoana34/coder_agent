"""自定义异常体系。所有可预期错误都归为 MiniCoderError 子类，便于上层统一处理。"""


class MiniCoderError(Exception):
    """本项目所有自定义异常的基类。"""


class ConfigError(MiniCoderError):
    """配置错误：缺少 API key、非法参数等。"""


class LLMError(MiniCoderError):
    """LLM API 调用错误：网络、认证、限流、超时等。"""


class ToolError(MiniCoderError):
    """工具执行错误（内部使用；工具对外失败时返回错误字符串而非抛此异常）。"""


class AgentTerminated(MiniCoderError):
    """Agent 被中断（如 Ctrl+C），需干净退出。"""
