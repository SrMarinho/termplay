"""UnoRuleset — toggleable rule variants for the Uno controller.

A ruleset bundles the optional rules that differ between the classic ("standard")
and Brazilian ("br") house rules. The controller reads these flags to decide how
draws, stacking and Wild+4 legality behave. Pure data, zero I/O.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, fields


@dataclass
class UnoRuleset:
    draw_then_play: bool = False      # standard: may play the drawn card if legal
    initial_card_effect: bool = False  # first discard card applies its action
    wild4_strict: bool = False        # wild4 illegal if a non-wild card is playable
    stack_draws: bool = False         # BR: +2/+4 accumulate across players
    draw_until_play: bool = False     # BR: draw until playable, then must play
    zero_swap: bool = False           # BR: playing a 0 swaps hands with a chosen player
    one_minigame: bool = False        # BR: playing a 1 triggers the tap-the-dot minigame
    multi_same_number: bool = False   # BR: play multiple cards of the same number in one turn

    @classmethod
    def standard(cls) -> UnoRuleset:
        return cls(draw_then_play=True, initial_card_effect=True, wild4_strict=True)

    @classmethod
    def brazilian(cls) -> UnoRuleset:
        # wild4 always legal (wild4_strict stays False)
        return cls(
            stack_draws=True, draw_until_play=True, zero_swap=True,
            one_minigame=True, multi_same_number=True,
        )

    @classmethod
    def from_name(cls, name: str) -> UnoRuleset:
        return {"standard": cls.standard, "br": cls.brazilian}.get(
            (name or "").lower(), cls.standard
        )()

    @classmethod
    def from_dict(cls, spec: dict) -> UnoRuleset:
        """Build from a flags mapping, ignoring unknown keys, defaulting missing."""
        valid = {f.name for f in fields(cls)}
        return cls(**{k: bool(v) for k, v in spec.items() if k in valid})

    @classmethod
    def from_spec(cls, spec: object) -> UnoRuleset:
        """Accept a preset name, a flags dict, or a JSON-encoded flags string."""
        if isinstance(spec, dict):
            return cls.from_dict(spec)
        if isinstance(spec, str):
            text = spec.strip()
            if text.startswith("{"):
                try:
                    return cls.from_dict(json.loads(text))
                except (ValueError, TypeError):
                    return cls.standard()
            return cls.from_name(text)
        return cls.standard()
