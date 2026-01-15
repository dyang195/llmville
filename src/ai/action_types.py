"""Data structures for open-ended action interpretation and resolution."""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class InterpretedAction:
    """An action extracted from dialogue by the LLM interpreter.

    Fully open-ended - no predefined categories. The description and intent
    are free-form text that the outcome resolver will interpret.
    """
    # Free-form description of what's being attempted
    description: str

    # Who is doing the action
    actor_id: str

    # Who/what is being acted upon
    target_id: str

    # The intent behind the action (e.g., "harm", "help", "deceive", "trade")
    intent: str = ""

    # Whether this involves physical contact/movement
    is_physical: bool = False

    # Whether this action ends the conversation (leaving, saying goodbye)
    ends_conversation: bool = False

    # Interpreter's confidence (0.0-1.0)
    confidence: float = 1.0


@dataclass
class ActionOutcome:
    """Result of attempting an action, determined by LLM."""
    # The original action
    action: InterpretedAction

    # Whether the action succeeded
    success: bool

    # Degree of success/failure (0.0-1.0)
    degree: float = 1.0

    # Effects to apply to the actor (free-form dict)
    # Examples: {"add_condition": "strained muscle", "gold": -10}
    actor_effects: dict[str, Any] = field(default_factory=dict)

    # Effects to apply to the target (free-form dict)
    # Examples: {"add_condition": "black eye", "health": -15, "gold": 10}
    target_effects: dict[str, Any] = field(default_factory=dict)

    # Narrative description of what happened (for narrator injection)
    narrative: str = ""

    # How this affects the relationship between actor and target
    relationship_delta: float = 0.0
