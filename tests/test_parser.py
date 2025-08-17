import pytest
from schema.schema import Command, Step, Constraints, Grasp
from safety.filter import validate_command

def test_pick_and_place():
    cmd = Command(
        steps=[
            Step(action="pick", object="red_cube", grasp=Grasp(approach_axis="z-")),
            Step(action="place", target="blue_box", constraints=Constraints(keep_vertical=True))
        ]
    )
    result = validate_command(cmd)
    assert result["ok"] == True

def test_out_of_bounds():
    cmd = Command(
        steps=[Step(action="move_ee", pose_xyzrpy=[1.2, 0.8, 0.7, 0, 0, 0])]
    )
    result = validate_command(cmd)
    assert result["error"] == "out_of_workspace"
