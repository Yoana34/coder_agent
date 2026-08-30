"""统计文本文件中的单词数。（故意留了 bug，供 agent 修复演示）"""

import sys


def count_words(text: str) -> int:
    # BUG: 只按单个空格切分 —— 连续空格会产生空串；换行符没有被当作分隔符
    words = text.split(" ")
    return len(words)


def main():
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    print(f"单词数: {count_words(text)}")


if __name__ == "__main__":
    main()
