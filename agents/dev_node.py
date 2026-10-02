"""开发角色节点 —— 经 DeepSeek Harness SDK 驱动，真实写代码。

特殊实现：不继承 BaseRoleNode，而是构造 DeepSeekHarness 上下文管理器，
把「技术方案」作为任务交给 DSH coding agent，让它用 bash 工具写代码。
"""

from __future__ import annotations

from harness.config import HarnessParams, RoleConfig
from harness.io import WorkspaceIO


class DevNode:
    """基于 DeepSeek Harness SDK 的开发角色节点。"""

    def __init__(self, role_cfg: RoleConfig, harness_params: HarnessParams):
        self.role_cfg = role_cfg
        self.harness_params = harness_params
        self.io = WorkspaceIO()

    def run(self, task: str, previous_artifact: str | None) -> dict:
        """把开发任务交给 DSH coding agent 执行。

        Args:
            task: 技术方案内容（作为开发任务的输入）
            previous_artifact: 保留参数，与 BaseRoleNode 接口对齐（此处即技术方案）

        Returns:
            {"content": 实现说明, "model": 模型名}
        """
        # 组装开发任务 prompt
        prompt = (
            f"{self.role_cfg.system_prompt}\n\n"
            f"以下是技术方案，请据此实现代码：\n\n"
            f"<technical-design>\n{task}\n</technical-design>\n\n"
            f"请将代码写入当前工作目录，并给出实现说明。"
        )

        # 导入 SDK（延迟导入，避免未安装时影响其他角色）
        try:
            from deepseek_harness import DeepSeekHarness
        except ImportError as e:
            raise RuntimeError(
                "未安装 deepseek-harness-sdk，请先：pip install deepseek-harness-sdk"
            ) from e

        p = self.harness_params
        with DeepSeekHarness(
            provider=p.provider,
            model=p.model,
            max_tokens=p.max_tokens,
            cwd=p.cwd,
            dsh_home=p.dsh_home,
            profile=p.profile,
        ) as harness:
            result = harness.run(
                prompt,
                session_id=f"dev-{self.io.sha256(task)[:8]}",
            )

        return {
            "content": result.final_response,
            "model": p.model,
        }
