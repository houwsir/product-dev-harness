#!/usr/bin/env python3
"""产品研发全流程 Agent Harness —— CLI 入口。

用法：
    python main.py --idea "做一个宠物领养小程序"

环境变量：
    DEEPSEEK_API_KEY  必填，DeepSeek API Key
    DEEPSEEK_BASE_URL 可选，自定义兼容网关

依赖安装：
    pip install -r requirements.txt
"""

from __future__ import annotations

import argparse

from harness.lifecycle import post_run_summary
from harness.runner import PipelineRunner


def main() -> int:
    parser = argparse.ArgumentParser(
        description="产品研发全流程 Agent Harness：从产品想法到代码骨架"
    )
    parser.add_argument(
        "--idea", required=True, help="产品想法（一句话描述）"
    )
    args = parser.parse_args()

    runner = PipelineRunner()
    print(f"🚀 开始产品研发全流程，产品想法：{args.idea}\n")

    try:
        result = runner.run(args.idea)
    except Exception as e:
        print(f"❌ 运行失败：{type(e).__name__}: {e}")
        return 1

    summary = post_run_summary(result)

    print("=" * 60)
    print(
        f"流水线完成：共 {summary['total_roles']} 角色，"
        f"成功 {summary['succeeded']}，失败 {summary['failed']}"
    )
    if summary["artifact_paths"]:
        print("\n产出工件：")
        for role, path in summary["artifact_paths"].items():
            print(f"  - {role}: {path}")
    if result["errors"]:
        print("\n错误：")
        for e in result["errors"]:
            print(f"  - {e}")
    print("=" * 60)

    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
