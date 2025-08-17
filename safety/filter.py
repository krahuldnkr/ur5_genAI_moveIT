from schema.schema import Command
from typing import Tuple

WORKSPACE_AABB = [[-0.4, 0.6], [-0.4, 0.6], [0.0, 0.6]]
VEL_CAP = 0.6
ACC_CAP = 0.6
ALLOWED_ACTIONS = {"pick", "place", "move_ee"}

def in_aabb(point: Tuple[float, float, float]) -> bool:
    return all(WORKSPACE_AABB[i][0] <= point[i] <= WORKSPACE_AABB[i][1] for i in range(3))

def validate_command(cmd: Command) -> dict:
    for step in cmd.steps:
        if step.action not in ALLOWED_ACTIONS:
            return {"error": "invalid_action", "hint": f"Use one of {ALLOWED_ACTIONS}"}

        if step.pose_xyzrpy:
            if not in_aabb(step.pose_xyzrpy[:3]):
                return {"error": "out_of_workspace", "hint": f"Target {step.pose_xyzrpy[:3]} outside workspace {WORKSPACE_AABB}"}

    if cmd.globals_.vel_scale > VEL_CAP:
        return {"error": "vel_too_high", "hint": f"Max vel_scale={VEL_CAP}"}

    if cmd.globals_.accel_scale > ACC_CAP:
        return {"error": "accel_too_high", "hint": f"Max accel_scale={ACC_CAP}"}

    return {"ok": True}
