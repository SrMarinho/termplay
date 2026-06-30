from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TrucoRuleset:
    mode: str = "2v2"
    mao_de_onze: bool = True

    @classmethod
    def from_spec(cls, spec: object) -> TrucoRuleset:
        if not isinstance(spec, dict):
            return cls()
        return cls(
            mode=spec.get("mode", "2v2"),
            mao_de_onze=bool(spec.get("mao_de_onze", True)),
        )

    @classmethod
    def duo(cls) -> TrucoRuleset:
        return cls(mode="1v1")

    @classmethod
    def team(cls) -> TrucoRuleset:
        return cls(mode="2v2")
