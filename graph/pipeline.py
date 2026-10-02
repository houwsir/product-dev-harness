"""LangGraph 流水线图定义。

职责：把五个角色节点串成静态串行图，
节点间只流转「工件内容」和「错误」，不流转各角色推理历史（独立上下文）。
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from agents.base import BaseRoleNode
from agents.dev_node import DevNode
from harness.config import ModelConfig, PipelineConfig, RoleConfig, load_all_roles
from harness.io import WorkspaceIO
from harness.validate import validate_artifact, validate_dev_workspace


def _merge_dict(left: dict, right: dict) -> dict:
    """合并两个字典（用于 artifacts / artifact_paths 的累加语义）。"""
    merged = dict(left)
    merged.update(right)
    return merged


def _sum(left: int, right: int) -> int:
    """整数累加（用于 succeeded / failed 计数）。"""
    return left + right


class PipelineState(TypedDict):
    """流水线共享状态。

    注意：这里只流转「工件」和「错误」，不流转任何角色的推理历史，
    因此各角色间上下文天然隔离。

    LangGraph 关键点：普通字段是「覆盖」语义，需要累加/合并的字段
    必须用 Annotated + reducer 声明，否则串行节点间会互相覆盖。
    """

    idea: str                                     # 原始产品想法（覆盖语义）
    artifacts: Annotated[dict[str, str], _merge_dict]   # {角色: 工件内容}（合并）
    errors: Annotated[list[str], operator.add]    # 错误回喂（累加）
    artifact_paths: Annotated[dict[str, str], _merge_dict]  # {角色: 工件路径}（合并）
    succeeded: Annotated[int, _sum]               # 成功角色数（累加）
    failed: Annotated[int, _sum]                  # 失败角色数（累加）


def _make_llm_node(role: str, node: BaseRoleNode, io: WorkspaceIO, model_name: str):
    """生成前四角色（pm/ba/arch/qa）的节点函数。"""

    def node_fn(state: PipelineState) -> dict:
        # 前序工件：串行流水线中，前一个角色的产出
        roles_order = ["pm", "ba", "arch", "dev", "qa"]
        idx = roles_order.index(role)
        previous_artifact = None
        if idx > 0:
            prev_role = roles_order[idx - 1]
            previous_artifact = state["artifacts"].get(prev_role)

        task = state["idea"] if role == "pm" else previous_artifact

        try:
            out = node.run(task, previous_artifact)
            content = out["content"]
            based_on = io.sha256(previous_artifact) if previous_artifact else "root"
            path = io.write_artifact(role, content, based_on, model_name)
            validate_artifact(role, path)
            return {
                "artifacts": {role: content},
                "artifact_paths": {role: path},
                "succeeded": 1,
            }
        except Exception as e:  # 错误回喂，不吞异常
            return {"errors": [f"[{role}] {type(e).__name__}: {e}"], "failed": 1}

    return node_fn


def _make_dev_node(node: DevNode, io: WorkspaceIO, model_name: str):
    """生成开发角色的节点函数。"""

    def node_fn(state: PipelineState) -> dict:
        arch_content = state["artifacts"].get("arch")
        if not arch_content:
            return {"errors": ["[dev] 缺少技术方案工件，无法开发"], "failed": 1}

        try:
            out = node.run(arch_content, arch_content)
            content = out["content"]
            based_on = io.sha256(arch_content)
            path = io.write_artifact("dev", content, based_on, model_name)
            # 开发角色额外校验：DSH 是否真的写盘（文件系统断言）
            from harness.config import PROJECT_ROOT

            dev_ws = PROJECT_ROOT / "workspace" / "dev-workspace"
            validate_dev_workspace(dev_ws)
            return {
                "artifacts": {"dev": content},
                "artifact_paths": {"dev": path},
                "succeeded": 1,
            }
        except Exception as e:
            return {"errors": [f"[dev] {type(e).__name__}: {e}"], "failed": 1}

    return node_fn


def build_graph(
    pipeline: PipelineConfig,
    model_cfg: ModelConfig,
    role_cfgs: dict[str, RoleConfig],
):
    """构建并编译 LangGraph 串行流水线图。"""
    from harness.config import build_chat_model, build_harness_params

    io = WorkspaceIO()
    chat_model = build_chat_model(model_cfg)
    harness_params = build_harness_params(model_cfg)

    # 前四角色统一用 BaseRoleNode（ChatDeepSeek）
    nodes: dict[str, BaseRoleNode | DevNode] = {}
    for name in ["pm", "ba", "arch", "qa"]:
        nodes[name] = BaseRoleNode(role_cfgs[name], chat_model, model_cfg.model)

    # 开发角色用 DevNode（DeepSeekHarness SDK）
    nodes["dev"] = DevNode(role_cfgs["dev"], harness_params)

    graph = StateGraph(PipelineState)

    for name in pipeline.roles:
        if name == "dev":
            graph.add_node(name, _make_dev_node(nodes[name], io, model_cfg.dsh_model))
        else:
            graph.add_node(
                name, _make_llm_node(name, nodes[name], io, model_cfg.model)
            )

    # 串行边
    for i in range(len(pipeline.roles) - 1):
        graph.add_edge(pipeline.roles[i], pipeline.roles[i + 1])

    graph.add_edge(START, pipeline.roles[0])
    graph.add_edge(pipeline.roles[-1], END)

    return graph.compile()
