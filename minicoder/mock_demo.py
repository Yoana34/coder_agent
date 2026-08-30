"""离线演示（--mock）场景：固定脚本 + 真实文件操作。

--mock 模式下 CLI 会先把 demo 场景 seed 到工作区，再用此脚本驱动一次
"读文件 → 定位 bug → 写文件修复 → 运行验证 → 总结"的完整闭环。
mock 只是代替 LLM 决策；工具调用由本地真实执行，且受工作区沙箱限制，
因此演示会真实地把工作区里的 buggy_wordcount.py 修复掉。
所有路径均为工作区内的相对路径。
"""

# 修复后的正确内容（write_file 工具将真实写入工作区）
FIXED_CONTENT = '''"""统计文本文件中的单词数。"""

import sys


def count_words(text: str) -> int:
    # 修复：split() 按任意空白切分并合并连续空白，正确处理换行与多余空格
    return len(text.split())


def main():
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"单词数: {count_words(text)}")


if __name__ == "__main__":
    main()
'''

MOCK_DEMO_TASK = (
    "buggy_wordcount.py 统计单词数有 bug（连续空格和换行没有正确处理，"
    "结果比实际偏少）。请阅读代码，修复它，并运行 sample.txt 验证。"
)

MOCK_DEMO_SCRIPT = [
    {
        "type": "tools",
        "tool_calls": [{"name": "read_file", "arguments": {"path": "buggy_wordcount.py"}}],
        "content": "我先阅读这个文件的代码，定位 bug。",
    },
    {
        "type": "tools",
        "tool_calls": [
            {
                "name": "write_file",
                "arguments": {"path": "buggy_wordcount.py", "content": FIXED_CONTENT},
            }
        ],
        "content": "问题在 count_words 使用 text.split(\" \")：连续空格会产生空串、换行未被当作分隔符，导致少计。改为 text.split()。",
    },
    {
        "type": "tools",
        "tool_calls": [
            {
                "name": "run_command",
                "arguments": {"command": "python buggy_wordcount.py sample.txt", "timeout": 30},
            }
        ],
        "content": "修改完成，运行验证。",
    },
    {
        "type": "final",
        "content": (
            "已修复。count_words 改用 text.split()（按任意空白切分并合并连续空白），"
            "示例文本现在正确统计为 11 个单词（修复前为 9）。"
        ),
    },
]
