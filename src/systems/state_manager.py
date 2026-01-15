"""Applies action effects to entity state."""

import logging
from typing import Any

from ..ai.action_types import ActionOutcome
from ..entities.person import Person
from ..entities.item import get_item

# Set up logging
logger = logging.getLogger("state_manager")
logger.setLevel(logging.DEBUG)


class StateManager:
    """Applies outcome effects to entity state."""

    def apply_outcome(
        self,
        outcome: ActionOutcome,
        actor: Person,
        target: Person,
        game_time: float = 0.0
    ):
        """
        Apply all effects from an action outcome.

        Args:
            outcome: The resolved action outcome
            actor: Person who performed the action
            target: Person who was acted upon
            game_time: Current game time for relationship updates
        """
        # Apply effects to both parties
        self._apply_effects(actor, outcome.actor_effects)
        self._apply_effects(target, outcome.target_effects)

        # Apply relationship change (target's feeling toward actor changes)
        if outcome.relationship_delta != 0:
            # Ensure relationship exists with proper name before updating
            target.get_relationship(actor.id, actor.name)
            target.update_relationship(
                other_id=actor.id,
                feeling_delta=outcome.relationship_delta,
                note=f"{outcome.action.description}",
                game_time=game_time
            )

    def _apply_effects(self, entity: Person, effects: dict[str, Any]):
        """
        Apply effect dictionary to an entity.

        Supported effect keys:
        - health: int/float - add to health (negative for damage)
        - gold: int/float - add to money (negative to remove)
        - add_condition: str - add a health condition
        - remove_condition: str - remove a health condition
        - add_item: str - add item by ID
        - remove_item: str - remove item by ID
        """
        if not effects:
            return

        logger.info(f"[STATE] Applying effects to {entity.name}: {effects}")

        for effect_type, value in effects.items():
            if value is None:
                continue

            if effect_type == "health":
                if value < 0:
                    entity.take_damage(abs(value))
                else:
                    entity.heal(value)

            elif effect_type == "gold":
                entity.money = max(0, entity.money + value)

            elif effect_type == "add_condition":
                if isinstance(value, str) and value:
                    entity.state.add_condition(value)

            elif effect_type == "remove_condition":
                if isinstance(value, str) and value:
                    entity.state.remove_condition(value)

            elif effect_type == "add_item":
                if isinstance(value, str):
                    item = get_item(value)
                    if item:
                        entity.add_item(item)

            elif effect_type == "add_items":
                # Handle array of items
                if isinstance(value, list):
                    for item_name in value:
                        item = get_item(item_name)
                        if item:
                            entity.add_item(item)

            elif effect_type == "remove_item":
                if isinstance(value, str):
                    entity.remove_item(value)

            elif effect_type == "remove_items":
                # Handle array of items
                if isinstance(value, list):
                    for item_name in value:
                        entity.remove_item(item_name)

            # Handle item with quantity (from trade/gift)
            elif effect_type == "give_item":
                if isinstance(value, dict):
                    item_id = value.get("item", "")
                    quantity = value.get("quantity", 1)
                    entity.remove_item(item_id, quantity)

            elif effect_type == "receive_item":
                if isinstance(value, dict):
                    item_id = value.get("item", "")
                    quantity = value.get("quantity", 1)
                    item = get_item(item_id)
                    if item:
                        entity.add_item(item, quantity)
