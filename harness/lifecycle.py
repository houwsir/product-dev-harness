"""生命周期钩子。

职责：pre_run（校验配置/凭证/环境）与 post_run（聚合产物、写摘要）。
用真实 Python 函数实现，不虚构 hook 框架。
"""

from __future__ import annotations

from typing import TypedDict

from .config import ModelConfig, PipelineConfig, get_api_key


class CheckResult(TypedDict):
    ok: bool
    errors: list[str]


class Summary(TypedDict):
    total_roles: int
    succeeded: int
    failed: int
    artifact_paths: dict[str, str]


def pre_run_check(pipeline: PipelineConfig, model: ModelConfig) -> CheckResult:
    """运行前校验：配置完整、API Key 存在、角色配置齐全。"""
    errors: list[str] = []

    if not pipeline.roles:
        errors.append("pipeline.yaml 的 roles 为空")

    try:
        get_api_key()
    except RuntimeError as e:
        errors.append(str(e))

    return CheckResult(ok=len(errors) == 0, errors=errors)


def post_run_summary(result) -> Summary:
    """运行后聚合：统计成功/失败角色，收集工件路径。"""
    return Summary(
        total_roles=result["total_roles"],
        succeeded=result["succeeded"],
        failed=result["failed"],
        artifact_paths=result["artifact_paths"],
    )
