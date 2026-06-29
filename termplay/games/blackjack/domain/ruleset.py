"""BlackjackRuleset — toggleable rule variants for the BlackjackVersusController."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields


@dataclass
class BlackjackRuleset:
    bust_penalty: bool = False  # busting deducts 1 point from the player's score

    @classmethod
    def default(cls) -> BlackjackRuleset:
        return cls()

    @classmethod
    def from_dict(cls, spec: dict) -> BlackjackRuleset:
        valid = {f.name for f in fields(cls)}
        return cls(**{k: bool(v) for k, v in spec.items() if k in valid})

    @classmethod
    def from_spec(cls, spec: object) -> BlackjackRuleset:
        if isinstance(spec, dict):
            return cls.from_dict(spec)
        if isinstance(spec, str):
            text = spec.strip()
            if text.startswith("{"):
                try:
                    return cls.from_dict(json.loads(text))
                except (ValueError, TypeError):
                    pass
        return cls.default()
