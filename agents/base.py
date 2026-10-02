"""角色节点基类。

前四角色（pm/ba/arch/qa）用 ChatDeepSeek，继承本类。
开发角色（dev）用 DeepSeekHarness SDK，单独实现（不继承，见 dev_node.py）。
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import BaseMessage

from harness.config import RoleConfig
from harness.context import assemble_context


class RoleOutput(TypedDict):
    """角色节点产出。"""

    content: str
    model: str


class BaseRoleNode:
    """基于 ChatDeepSeek 的角色节点。"""

    def __init__(self, role_cfg: RoleConfig, chat_model, model_name: str):
        self.role_cfg = role_cfg
        self.chat_model = chat_model
        self.model_name = model_name

    def run(self, task: str, previous_artifact: str | None) -> RoleOutput:
        messages: list[BaseMessage] = assemble_context(
            self.role_cfg, task, previous_artifact
        )
        resp = self.chat_model.invoke(messages)
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return RoleOutput(content=content, model=self.model_name)
