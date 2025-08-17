# main.py
import sys
from glue.compile import compile_prompt_to_command

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "Pick the red cube and place it on the blue box. Keep the gripper vertical."
    cmd = compile_prompt_to_command(prompt)
    print(cmd.model_dump_json(indent=2))   # pretty JSON (Pydantic v2)
