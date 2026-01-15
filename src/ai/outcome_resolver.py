"""LLM-based outcome resolution for actions.

Fully open-ended - the LLM determines success, effects, and narrative
based on the action and character states. No hardcoded rules.
"""

import json
import logging
from typing import Any

from .action_types import InterpretedAction, ActionOutcome
from .claude_client import ClaudeClient
from ..entities.person import Person

# Set up logging
logger = logging.getLogger("outcome_resolver")
logger.setLevel(logging.DEBUG)


class OutcomeResolver:
    """Uses LLM to resolve action outcomes."""

    def __init__(self, claude_client: ClaudeClient):
        self.claude_client = claude_client

    def resolve(
        self,
        action: InterpretedAction,
        actor: Person,
        target: Person,
        conversation_context: list[dict] = None
    ) -> ActionOutcome:
        """
        Determine the outcome of an action attempt using LLM.

        Args:
            action: The interpreted action
            actor: Person performing the action
            target: Person being acted upon
            conversation_context: Full conversation for understanding context

        Returns:
            ActionOutcome with success, effects, and narrative
        """
        system_prompt = self._build_resolver_prompt()
        user_message = self._build_action_context(action, actor, target, conversation_context)

        logger.info(f"[RESOLVER] Resolving action: {action.description}")
        logger.debug(f"[RESOLVER] Actor: {actor.name} (HP: {actor.health:.0f}, Gold: {actor.money:.0f})")
        logger.debug(f"[RESOLVER] Target: {target.name} (HP: {target.health:.0f}, Gold: {target.money:.0f})")

        response = self.claude_client.generate_outcome_sync(
            system_prompt=system_prompt,
            user_message=user_message
        )

        logger.debug(f"[RESOLVER] Raw LLM response:\n{response}")

        outcome = self._parse_outcome(response, action, actor, target)

        logger.info(f"[RESOLVER] Outcome: success={outcome.success}, degree={outcome.degree:.2f}")
        if outcome.actor_effects:
            logger.info(f"[RESOLVER] Actor effects: {outcome.actor_effects}")
        if outcome.target_effects:
            logger.info(f"[RESOLVER] Target effects: {outcome.target_effects}")
        if outcome.narrative:
            logger.info(f"[RESOLVER] Narrative: {outcome.narrative}")

        return outcome

    def _build_resolver_prompt(self) -> str:
        """Build the system prompt for outcome resolution."""
        return """You are an outcome resolver for a social simulation game. You see the full conversation and must determine what state changes result from an action.

## Your Job

Look at the CONVERSATION CONTEXT to understand:
- What was being negotiated or discussed
- What has [Already resolved] (don't apply those effects again)
- What the current action means in context

Then determine ALL state changes that should happen NOW.

## Output Format

Respond with ONLY this JSON:
{
  "success": true/false,
  "degree": 0.0-1.0,
  "relationship_delta": -0.5 to 0.5,
  "narrative": "Brief description of what happened.",
  "actor_effects": {
    "health": number or null,
    "gold": number or null,
    "add_condition": "condition" or null,
    "add_items": ["item1", "item2"] or null,
    "remove_items": ["item1", "item2"] or null
  },
  "target_effects": {
    "health": number or null,
    "gold": number or null,
    "add_condition": "condition" or null,
    "add_items": ["item1", "item2"] or null,
    "remove_items": ["item1", "item2"] or null
  }
}

Note: add_items and remove_items are ARRAYS - use them for one or more items.

## Key Points

- Use the conversation to understand the FULL context of what's happening
- If this is part of a trade/purchase, include ALL effects (gold AND items for both parties)
- Check [Already resolved] markers - don't double-apply effects

## Narrative Style

KEEP IT SHORT. Just state the action. No fluff.

WRONG: "Edward completes the transaction by paying Charlotte 6 gold for the bread, finalizing their negotiated purchase."
CORRECT: "Edward gives Charlotte 6 gold."

WRONG: "The punch connects with Marcus's jaw, leaving him reeling from the impact."
CORRECT: "James punches Marcus. (-10 health)"

Just: [Who] [did what] [to whom]. Include numbers if relevant. Nothing else."""

    def _build_action_context(
        self,
        action: InterpretedAction,
        actor: Person,
        target: Person,
        conversation_context: list[dict] = None
    ) -> str:
        """Build the context message for the LLM."""
        actor_conditions = actor.state.get_conditions_string()
        target_conditions = target.state.get_conditions_string()

        # Format conversation so resolver understands full context
        conv_text = ""
        if conversation_context:
            conv_lines = []
            for msg in conversation_context:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                if content.startswith("[Narrator:"):
                    conv_lines.append(f"[Already resolved: {content[10:-1]}]")
                else:
                    speaker = actor.name if role == "assistant" else target.name
                    conv_lines.append(f"{speaker}: {content}")
            conv_text = "\n".join(conv_lines)

        return f"""## CONVERSATION SO FAR
{conv_text if conv_text else "(Just started)"}

## ACTION TO RESOLVE
{actor.name} is attempting: {action.description}

## CURRENT STATE

{actor.name} (actor):
- Gold: {actor.money:.0f}
- Inventory: {actor.get_inventory_string()}
- Health: {actor.health:.0f}/{actor.max_health:.0f}
- Conditions: {actor_conditions}

{target.name} (target):
- Gold: {target.money:.0f}
- Inventory: {target.get_inventory_string()}
- Health: {target.health:.0f}/{target.max_health:.0f}
- Conditions: {target_conditions}

Based on the conversation and action, determine ALL state changes that should result."""

    def _format_traits(self, person: Person) -> str:
        """Format personality traits for context."""
        traits = person.personality.traits
        high_traits = [k for k, v in traits.items() if v > 0.7]
        low_traits = [k for k, v in traits.items() if v < 0.3]

        parts = []
        if high_traits:
            parts.append(f"high {', '.join(high_traits)}")
        if low_traits:
            parts.append(f"low {', '.join(low_traits)}")

        return "; ".join(parts) if parts else "average"

    def _parse_outcome(
        self,
        response: str,
        action: InterpretedAction,
        actor: Person,
        target: Person
    ) -> ActionOutcome:
        """Parse the LLM response into an ActionOutcome."""
        try:
            # Find JSON in response
            response = response.strip()
            start = response.find("{")
            end = response.rfind("}") + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

            # Extract effects, defaulting to empty dicts
            actor_effects = self._normalize_effects(data.get("actor_effects", {}))
            target_effects = self._normalize_effects(data.get("target_effects", {}))
            success = data.get("success", False)

            # Use AI-generated narrative, fall back to programmatic if missing
            narrative = data.get("narrative", "")
            if not narrative and (actor_effects or target_effects):
                narrative = self._generate_factual_narrative(
                    action, actor, target, success, actor_effects, target_effects
                )

            return ActionOutcome(
                action=action,
                success=success,
                degree=data.get("degree", 0.5),
                actor_effects=actor_effects,
                target_effects=target_effects,
                narrative=narrative,
                relationship_delta=data.get("relationship_delta", 0.0)
            )

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            print(f"Failed to parse outcome: {e}")
            # Return a neutral outcome on parse failure
            return ActionOutcome(
                action=action,
                success=False,
                degree=0.0,
                actor_effects={},
                target_effects={},
                narrative="",
                relationship_delta=0.0
            )

    def _generate_factual_narrative(
        self,
        action: InterpretedAction,
        actor: Person,
        target: Person,
        success: bool,
        actor_effects: dict,
        target_effects: dict
    ) -> str:
        """Generate objective, factual narrative from action effects.

        Format: "Actor does X to Target. Target loses Y health. Target gains condition Z."
        Only generates narrative if there are actual state changes.
        """
        # If no effects, no narrative needed
        if not actor_effects and not target_effects:
            return ""

        parts = []

        # Describe target effects (most important)
        if target_effects:
            health_change = target_effects.get("health", 0)
            if health_change < 0:
                parts.append(f"{target.name} loses {abs(health_change):.0f} health")

            condition = target_effects.get("add_condition")
            if condition:
                parts.append(f"{target.name} suffers {condition}")

            gold_change = target_effects.get("gold", 0)
            if gold_change > 0:
                parts.append(f"{target.name} receives {gold_change:.0f} gold")
            elif gold_change < 0:
                parts.append(f"{target.name} loses {abs(gold_change):.0f} gold")

            item_received = target_effects.get("add_item")
            if item_received:
                parts.append(f"{target.name} receives {item_received}")

            item_lost = target_effects.get("remove_item")
            if item_lost:
                parts.append(f"{target.name} loses {item_lost}")

        # Describe actor effects
        if actor_effects:
            health_change = actor_effects.get("health", 0)
            if health_change < 0:
                parts.append(f"{actor.name} loses {abs(health_change):.0f} health")

            condition = actor_effects.get("add_condition")
            if condition:
                parts.append(f"{actor.name} suffers {condition}")

            gold_change = actor_effects.get("gold", 0)
            if gold_change > 0:
                parts.append(f"{actor.name} receives {gold_change:.0f} gold")
            elif gold_change < 0:
                parts.append(f"{actor.name} loses {abs(gold_change):.0f} gold")

            item_received = actor_effects.get("add_item")
            if item_received:
                parts.append(f"{actor.name} receives {item_received}")

            item_lost = actor_effects.get("remove_item")
            if item_lost:
                parts.append(f"{actor.name} loses {item_lost}")

        if not parts:
            return ""

        return ". ".join(parts) + "."

    def _normalize_effects(self, effects: dict[str, Any]) -> dict[str, Any]:
        """Normalize effects dict, removing null/None values."""
        if not effects:
            return {}

        normalized = {}
        for key, value in effects.items():
            if value is not None and value != 0:
                normalized[key] = value

        return normalized
