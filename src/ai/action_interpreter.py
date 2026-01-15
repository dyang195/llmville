"""LLM-based action interpretation from dialogue.

Fully open-ended - no predefined action categories. The LLM extracts
what's happening in natural language.
"""

import json
import logging
import re
from typing import Optional

from .action_types import InterpretedAction
from .claude_client import ClaudeClient
from ..entities.person import Person

# Set up logging
logger = logging.getLogger("action_interpreter")
logger.setLevel(logging.DEBUG)

# Pattern to detect action markers like *hands over gold*
ACTION_MARKER_PATTERN = re.compile(r'\*[^*]+\*')


class ActionInterpreter:
    """Uses LLM to extract actions from natural dialogue."""

    def __init__(self, claude_client: ClaudeClient):
        self.claude_client = claude_client

    def interpret(
        self,
        dialogue_text: str,
        speaker: Person,
        listener: Person,
        conversation_context: list[dict]
    ) -> Optional[InterpretedAction]:
        """
        Analyze dialogue and extract any attempted action.

        Args:
            dialogue_text: The most recent message to interpret
            speaker: Person who said the dialogue
            listener: Person being spoken to
            conversation_context: Recent messages for context

        Returns:
            InterpretedAction if an action was detected, None otherwise
        """
        # Quick check: only run LLM if there's an action marker like *does something*
        if not ACTION_MARKER_PATTERN.search(dialogue_text):
            logger.debug(f"[INTERPRETER] No action markers in dialogue, skipping LLM")
            return None

        system_prompt = self._build_interpreter_prompt(speaker, listener)
        context_text = self._format_context(conversation_context)

        user_message = f"""## Recent Conversation
{context_text}

## Latest Message (from {speaker.name}):
"{dialogue_text}"

Analyze this message. Is the speaker attempting any ACTION (not just talking)?"""

        logger.info(f"[INTERPRETER] Analyzing dialogue from {speaker.name}: \"{dialogue_text}\"")

        response = self.claude_client.generate_interpretation_sync(
            system_prompt=system_prompt,
            user_message=user_message
        )

        logger.debug(f"[INTERPRETER] Raw LLM response:\n{response}")

        result = self._parse_interpretation(response, speaker.id, listener.id)

        if result:
            logger.info(f"[INTERPRETER] ACTION DETECTED: {result.description} (intent: {result.intent}, physical: {result.is_physical})")
        else:
            logger.debug(f"[INTERPRETER] No action detected")

        return result

    def _build_interpreter_prompt(self, speaker: Person, listener: Person) -> str:
        """Build the system prompt for action interpretation."""
        speaker_conditions = speaker.state.get_conditions_string()
        listener_conditions = listener.state.get_conditions_string()

        return f"""You are an action interpreter for a social simulation. Detect actions that would meaningfully change a character's state or metadata.

## Characters

SPEAKER: {speaker.name}
- Role: {speaker.role.role_type.value}
- Health: {speaker.health:.0f}/{speaker.max_health:.0f}
- Conditions: {speaker_conditions}
- Inventory: {speaker.get_inventory_string()}
- Gold: {speaker.money:.0f}

LISTENER: {listener.name}
- Role: {listener.role.role_type.value}
- Health: {listener.health:.0f}/{listener.max_health:.0f}
- Conditions: {listener_conditions}
- Inventory: {listener.get_inventory_string()}
- Gold: {listener.money:.0f}

## What to Detect

Detect ANY action that would result in a meaningful change to character state. Be creative! Examples:
- Violence (punches, kicks, shoves) → health/condition changes
- Giving/taking items or gold → inventory/money changes
- Theft attempts → inventory changes
- Actually leaving the conversation → ends interaction
- Any action with real consequences

Only detect when the action is ACTUALLY HAPPENING in this message (marked with *asterisks* typically):
- "*hands over 5 gold*" → DETECT
- "*punches him*" → DETECT
- "Would you like to buy this?" → NOT an action, just talking

The conversation history includes [RESOLVED ACTION] markers - the resolver will handle avoiding duplicates.

## What to IGNORE (Mundane Gestures)

Skip actions that are just flavor text with no state change:
- Looking, glancing, gazing
- Leaning, sitting, standing, positioning
- Nodding, smiling, frowning, sighing
- Crossing arms, tilting head, shrugging
- Waving, pointing, gesturing
- Any expression of emotion without action

The key question: "Would this change any character data (health, conditions, inventory, gold, relationships, metadata)?"
- If YES → detect it
- If NO → skip it

## Output Format

Respond with ONLY this JSON:
{{
  "action_detected": false
}}

OR if a meaningful action is detected:
{{
  "action_detected": true,
  "description": "ONLY what is literally in the *asterisks* - nothing more",
  "intent": "the goal (harm, help, steal, give, leave, change identity, etc.)",
  "is_physical": true/false,
  "ends_conversation": true/false
}}

## Rules
1. DEFAULT TO NO ACTION - most messages are just dialogue
2. Only detect physical actions happening NOW, not offers or proposals
3. Description must be LITERAL - only what's in the *asterisks*

WRONG description: "Harold is paying 8 gold for an apple" (inferred context)
CORRECT description: "hands over 8 gold" (literal action)

WRONG description: "completing the bread purchase by giving gold" (inferred)
CORRECT description: "hands over 5 gold" (literal)

The resolver will figure out the context - just tell it the literal action."""

    def _format_context(self, messages: list[dict]) -> str:
        """Format full conversation history for context.

        Includes all messages so the AI can see what actions have already
        been resolved and avoid re-detecting them.
        """
        if not messages:
            return "(Conversation just started)"

        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Mark narrator messages as resolved actions so AI knows not to re-detect
            if content.startswith("[Narrator:"):
                # Transform [Narrator: X] to [RESOLVED ACTION: X]
                action_text = content[10:-1]  # Strip "[Narrator:" and trailing "]"
                lines.append(f"[RESOLVED ACTION: {action_text}]")
            else:
                lines.append(f"- {role}: {content}")
        return "\n".join(lines)

    def _parse_interpretation(
        self,
        response: str,
        actor_id: str,
        target_id: str
    ) -> Optional[InterpretedAction]:
        """Parse the LLM response into an InterpretedAction."""
        try:
            # Try to extract JSON from response
            # Sometimes the LLM includes extra text
            response = response.strip()

            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
            else:
                return None

            if not data.get("action_detected", False):
                return None

            return InterpretedAction(
                description=data.get("description", ""),
                actor_id=actor_id,
                target_id=target_id,
                intent=data.get("intent", ""),
                is_physical=data.get("is_physical", False),
                ends_conversation=data.get("ends_conversation", False),
                confidence=data.get("confidence", 1.0)
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Failed to parse interpretation: {e}")
            return None
