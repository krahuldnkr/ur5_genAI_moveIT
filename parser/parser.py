def parse_command(text):
    text = text.lower()
    steps = []

    # step 1: check for 'pick'
    if "pick" in text:
        if "red cube" in text:
            steps.append({"action": "pick", "object": "red_cube"})

    # step 2: check for 'place' or 'put'
    if "place" in text or "put" in text:
        if "blue box" in text:
            steps.append({"action": "place", "target": "blue_box"})

    # step 3: check for constraint
    constraints = {}
    if "vertical" in text:
        constraints["keep_vertical"] = True
        # attach constraint to last step if exists
        if steps:
            steps[-1]["constraints"] = constraints

    return {"steps": steps}

# try it out
cmd = "Pick the red cube and place it on the blue box, keep the gripper vertical."
print(parse_command(cmd))
