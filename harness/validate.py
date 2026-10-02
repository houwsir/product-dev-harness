"""确定性工件校验。

职责：不靠模型自评，用纯代码校验工件是否真实产出。
对开发角色（DSH 写文件），额外做文件系统断言 —— 工具回执 ≠ 业务事实。
"""

from __future__ import annotations

from pathlib import Path
from typing import TypedDict


class ValidationResult(TypedDict):
    ok: bool
    message: str


def validate_artifact(role: str, path: str) -> ValidationResult:
    """校验工件文件存在、非空。"""
    p = Path(path)
    if not p.exists():
        return ValidationResult(ok=False, message=f"工件文件不存在：{path}")
    size = p.stat().st_size
    if size == 0:
        return ValidationResult(ok=False, message=f"工件文件为空：{path}")
    return ValidationResult(ok=True, message=f"工件 {role} 校验通过（{size} 字节）")


def validate_dev_workspace(workspace: Path) -> ValidationResult:
    """开发角色专属：核对 DSH 是否真的写入了代码文件。

    不能只信 DSH 的 bash 工具回执（退出码 0），
    必须核对文件系统里实际产出了文件。
    """
    if not workspace.exists():
        return ValidationResult(ok=False, message="开发工作目录不存在")

    files = [f for f in workspace.rglob("*") if f.is_file()]
    if not files:
        return ValidationResult(
            ok=False, message="开发角色未产出任何文件（DSH 未实际写盘）"
        )
    return ValidationResult(
        ok=True,
        message=f"开发角色产出 {len(files)} 个文件",
    )
