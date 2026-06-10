from pathlib import Path


def _resolve_rules_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "rules"


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        raise ValueError("Rule file must start with --- frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Rule file must have closing --- for frontmatter")
    frontmatter = parts[1].strip()
    body = parts[2].strip()
    config = {}
    for line in frontmatter.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if not value:
            continue
        try:
            config[key] = int(value)
            continue
        except ValueError:
            pass
        if value.lower() in ("true", "false"):
            config[key] = value.lower() == "true"
            continue
        if "," in value:
            config[key] = [v.strip() for v in value.split(",") if v.strip()]
            continue
        config[key] = value
    return config, body


def load_rule(name: str) -> dict:
    path = _resolve_rules_dir() / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Rule file not found: {path}")
    text = path.read_text(encoding="utf-8")
    config, body = _parse_frontmatter(text)
    config["system_prompt"] = body
    return config
