# Clarifier policy: one clarifying question max.

def clarify(user_input: str, known_objects: list[str]) -> dict:
    # naive example
    if "it" in user_input.lower():
        return {
            "question": f"Which object should I pick? Options: {known_objects}"
        }
    return {"ok": True}
