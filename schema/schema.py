from pydantic import BaseModel, Field
from typing import List, Optional, Dict

# This schema guarantees that whatever comes out of the parser is 
# structured, validated, and robot-ready.
# MoveIt doesn't have to parse free-text- it just cosumes the JSON and executes.
class Grasp(BaseModel):
    """ info for how the robot should approach an object.

    Args:
        BaseModel (object): has built-in validation, type-checking, defaults,
        and serialisation.

    """

    # approach the cube along -z
    approach_axis: str = Field(..., description="Direction of approach, e.g. 'z-'")
    # 8 cm away before closing the gripper
    pregrasp_m: float = 0.08
    # use case: pick up the cube from top

class Constraints(BaseModel):
    """ movement restrictions.

    Args:
        BaseModel (object): has built-in validation, type-checking, defaults,
        and serialisation.

    """
    # enforces the gripper stays upright: useful when carrying liquid
    keep_vertical: bool = False
    # safety buffer aroud obstacles (default 3 cm)
    clearance_m: float = 0.03

class Step(BaseModel):
    """ the atomic instruction (like one verb in a sentence).

    Args:
        BaseModel (object): has built-in validation, type-checking, defaults,
        and serialisation.

    """
    # move end effector: "pick" or "place" or "move_ee"
    action: str = Field(..., description="pick | place | move_ee")
    # name of object, e.g. "cube red"
    object: Optional[str] = None   
    # where to place/move, e.g. "bin_A"
    target: Optional[str] = None
    # reference frame (e.g. "world", "table", "camera_link")
    frame: Optional[str] = None
    # location and orientation.
    pose_xyzrpy: Optional[List[float]] = None
    # translation offset [dx, dy, dz].
    offset_xyz: Optional[List[float]] = None
    # nested grasp object.
    grasp: Optional[Grasp] = None
    # nested Constraints object.
    constraints: Optional[Constraints] = None
    # if True, use cartesian path planning, else joint-space.
    cartesian: Optional[bool] = False

class Globals(BaseModel):
    """ these set global parameters that apply to all steps (unless overridden).

    Args:
        BaseModel (object): has built-in validation, type-checking, defaults,
        and serialisation.

    """
    # scales max velocity: (0.5 is 50% of max) 
    vel_scale: float = 0.5
    # scales acceleration: (0.3 = 30% of max)
    accel_scale: float = 0.3

class Command(BaseModel):
    """ Top-level container = a full parsed command (sequence of steps).

    Args:
        BaseModel (object): has built-in validation, type-checking, defaults,
        and serialisation.

    """
    # list of step objects
    steps: List[Step]
    # global motion parameters
    globals_: Globals = Field(default_factory=Globals, alias="globals")

from pydantic import ValidationError

if __name__ == "__main__":
    #  Example 1: valid command
    try:
        cmd = Command(
            steps=[
                Step(
                    action="pick",
                    object="cube",
                    frame="world",
                    pose_xyzrpy=[0.5, 0.1, 0.2, 0, 0, 0],
                    grasp=Grasp(approach_axis="z-"),
                    constraints=Constraints(keep_vertical=True)
                ),
                Step(
                    action="place",
                    target="bin",
                    offset_xyz=[0, 0, 0.1]
                )
            ],
            globals_={
                "vel_scale": 0.7,
                "accel_scale": 0.5
            }
        )
        print("Valid Command Parsed:")
        print(cmd.model_dump_json(indent=2))  # pretty JSON output

    except ValidationError as e:
        print("Validation Error in Example 1:")
        print(e)

    print("="*50)

    # # Example 2: invalid command (missing action + wrong type)
    # try:
    #     bad_cmd = Command(
    #         steps=[
    #             Step(
    #                 pose_xyzrpy="not_a_list"  #  should be List[float]
    #             )
    #         ]
    #     )
    # except ValidationError as e:
    #     print(" Validation Error in Example 2:")
    #     print(e)
