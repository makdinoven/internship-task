import uuid


def uniq_email(prefix: str = "u") -> str:
    return f"{prefix}_{uuid.uuid4().hex}@example.com"
