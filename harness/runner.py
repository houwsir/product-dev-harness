"""流水线运行器。

职责：加载配置 → 预检 → 建图 → 跑图 → 聚合结果。
"""

from __future__ import annotations

from typing import TypedDict

from graph.pipeline import PipelineState, build_graph
from harness.config import (
    load_all_roles,
    load_model_config,
    load_pipeline,
)
from harness.lifecycle import pre_run_check


class RunResult(TypedDict):
    ok: bool
    total_roles: int
    succeeded: int
    failed: int
    artifact_paths: dict[str, str]
    errors: list[str]


class PipelineRunner:
    """产品研发全流程流水线运行器。"""

    def __init__(self, config_dir: str | None = None):
        self.pipeline = load_pipeline()
        self.model_cfg = load_model_config()
        self.role_cfgs = load_all_roles(self.pipeline)

    def run(self, idea: str) -> RunResult:
        """运行整条流水线。

        Args:
            idea: 产品想法（一句话描述）

        Returns:
            RunResult 聚合结果
        """
        if not idea or not idea.strip():
            raise ValueError("产品想法不能为空")

        # 预检
        check = pre_run_check(self.pipeline, self.model_cfg)
        if not check["ok"]:
            return RunResult(
                ok=False,
                total_roles=len(self.pipeline.roles),
                succeeded=0,
                failed=len(self.pipeline.roles),
                artifact_paths={},
                errors=check["errors"],
            )

        # 建图 + 跑图
        graph = build_graph(self.pipeline, self.model_cfg, self.role_cfgs)

        initial_state: PipelineState = {
            "idea": idea.strip(),
            "artifacts": {},
            "errors": [],
            "artifact_paths": {},
            "succeeded": 0,
            "failed": 0,
        }

        result = graph.invoke(initial_state)

        return RunResult(
            ok=result.get("failed", 0) == 0,
            total_roles=len(self.pipeline.roles),
            succeeded=result.get("succeeded", 0),
            failed=result.get("failed", 0),
            artifact_paths=result.get("artifact_paths", {}),
            errors=result.get("errors", []),
        )
