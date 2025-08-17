# glue/compile.py
from pydantic import ValidationError
from schema.schema import Command
from parser.parser import parse_command

def compile_prompt_to_command(prompt: str) -> Command:
    """ the function promises to return a validated schema object

    """
    raw = parse_command(prompt)              # dict from parser
    try:
        # checks if the raw matches with the schema 
        cmd = Command.model_validate(raw)    # Pydantic v2: validate + coerce
        # cmd is safe, typed, and structured
        return cmd
    except ValidationError as e:
        # bubble up a clean error (or trigger your clarifier)
        raise ValueError(f"schema_validation_failed: {e.errors()}")
