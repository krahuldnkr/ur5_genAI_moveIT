# parser/parser.py
def parse_command(text: str) -> dict:
    text = text.lower()
    steps = []
    if "pick" in text and "red cube" in text:
        steps.append({
            "action": "pick",
            "object": "red_cube",
            "grasp": {"approach_axis": "z-", "pregrasp_m": 0.08},
            "constraints": {"keep_vertical": "vertical" in text, "clearance_m": 0.03}
        })
    if ("place" in text or "put" in text) and "blue box" in text:
        steps.append({
            "action": "place",
            "target": "blue_box",
            "offset_xyz": [0.0, 0.0, 0.10]
        })
    return {
        "steps": steps,
        "globals": {"vel_scale": 0.5, "accel_scale": 0.3}  # note: "globals" (alias)
    }

# try it out
cmd = "Pick the red cube and place it on the blue box, keep the gripper vertical."
print(parse_command(cmd))
