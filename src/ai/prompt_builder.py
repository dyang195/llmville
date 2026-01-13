"""System prompt construction from entity data."""

import config
from ..entities.person import Person, Relationship
from ..core.time_manager import TimeManager


class PromptBuilder:
    """Constructs system prompts for AI conversations."""

    def build_conversation_prompt(
        self,
        speaker: Person,
        listener: Person,
        time_manager: TimeManager = None,
        turn_number: int = 0,
        max_turns: int = None
    ) -> str:
        """Build system prompt for a conversation turn."""
        personality_desc = self._build_personality_description(speaker)
        relationship_desc = self._build_relationship_description(speaker, listener)
        inventory_desc = speaker.get_inventory_string()

        if max_turns is None:
            max_turns = config.MAX_CONVERSATION_TURNS

        # Time context
        if time_manager:
            time_context = f"- Time: {time_manager.get_time_string()} ({time_manager.get_time_of_day()}) on Day {time_manager.day}"
        else:
            time_context = "- Time: Daytime"

        # Conversation phase guidance
        if turn_number >= max_turns - 1:
            phase_hint = "\n\n**This conversation has been going on a while. You should wrap up and say goodbye soon. Use [END_CONVERSATION] after your farewell.**"
        elif turn_number >= max_turns - 2:
            phase_hint = "\n\n*The conversation is winding down. Consider wrapping up naturally.*"
        else:
            phase_hint = ""

        prompt = f"""You are {speaker.name}, a {speaker.role.role_type.value} in a small town.

## Your Personality
{personality_desc}

## Current Situation
{time_context}
- Your health: {speaker.health:.0f}/{speaker.max_health:.0f}
- Your money: {speaker.money:.0f} gold
- Your inventory: {inventory_desc}

## Your Relationship with {listener.name}
{relationship_desc}

## Conversation Instructions
- Stay completely in character as {speaker.name}
- Your responses should reflect your personality traits
- Keep responses to 1-2 sentences (this is casual town conversation)
- Consider your relationship history when responding
- Conversations should be brief and natural - don't drag them out

## Actions (include at END of your response when appropriate)
- To propose a trade: [TRADE: OFFER item_name FOR item_name_or_gold_amount]
- To give a gift: [GIFT: item_name]
- **To end the conversation and say goodbye: [END_CONVERSATION]**

End conversations naturally after a few exchanges. Say your goodbye, then add [END_CONVERSATION].{phase_hint}"""

        return prompt

    def _build_personality_description(self, person: Person) -> str:
        """Generate natural language personality description."""
        p = person.personality

        # Describe traits
        trait_descriptions = []
        for trait, value in p.traits.items():
            if value > 0.7:
                trait_descriptions.append(f"very {trait}")
            elif value > 0.5:
                trait_descriptions.append(f"somewhat {trait}")
            elif value < 0.3:
                trait_descriptions.append(f"not very {trait}")

        traits_text = ", ".join(trait_descriptions[:4]) if trait_descriptions else "average in most regards"

        # Quirks
        quirks_text = "; ".join(p.quirks) if p.quirks else "no particular quirks"

        # Goals
        goals_text = "; ".join(p.goals) if p.goals else "live a peaceful life"

        return f"""{p.background}

Personality traits: You are {traits_text}.
Speech style: You speak in a {p.speech_style} manner.
Quirks: {quirks_text}
Current goals: {goals_text}"""

    def _build_relationship_description(self, speaker: Person, listener: Person) -> str:
        """Build description of relationship for prompt."""
        if listener.id not in speaker.relationships:
            return f"You don't know {listener.name} yet. This is your first meeting."

        rel = speaker.relationships[listener.id]

        # More nuanced feeling description
        feeling = rel.feeling_score
        if feeling > 0.7:
            feeling_desc = f"You consider {listener.name} a close friend and trust them"
        elif feeling > 0.4:
            feeling_desc = f"You like {listener.name} and enjoy their company"
        elif feeling > 0.1:
            feeling_desc = f"You have a positive impression of {listener.name}"
        elif feeling > -0.1:
            feeling_desc = f"You feel neutral about {listener.name}"
        elif feeling > -0.4:
            feeling_desc = f"You're wary of {listener.name}"
        elif feeling > -0.7:
            feeling_desc = f"You dislike {listener.name}"
        else:
            feeling_desc = f"You strongly distrust {listener.name}"

        # History
        if rel.history:
            history_text = "Recent interactions:\n- " + "\n- ".join(rel.history[-3:])
        else:
            history_text = "No significant past interactions."

        # Notes - these are the detailed observations
        if rel.notes:
            notes_text = "Your observations about them:\n- " + "\n- ".join(rel.notes[-5:])
        else:
            notes_text = ""

        parts = [
            feeling_desc + f". You've spoken {rel.interaction_count} times before.",
            history_text
        ]
        if notes_text:
            parts.append(notes_text)

        return "\n".join(parts)

    def build_reflection_prompt(
        self,
        speaker: Person,
        other: Person,
        conversation_messages: list[dict]
    ) -> str:
        """Build prompt for post-conversation reflection to generate detailed notes."""
        conv_text = "\n".join([
            f"{m['role'].title()}: {m['content']}"
            for m in conversation_messages
        ])

        existing_notes = ""
        if other.id in speaker.relationships:
            rel = speaker.relationships[other.id]
            if rel.notes:
                existing_notes = "Your previous observations:\n- " + "\n- ".join(rel.notes[-3:])

        return f"""You are {speaker.name}, a {speaker.role.role_type.value}. You just finished a conversation with {other.name}.

{existing_notes}

## The Conversation
{conv_text}

## Your Task
Reflect on this conversation from {speaker.name}'s perspective. Provide:

1. SUMMARY: A brief 1-sentence summary of what happened
2. FEELING: A number from -0.3 to +0.3 indicating how this changed your feelings toward {other.name}
   - Positive if the conversation was pleasant, helpful, or you learned something good about them
   - Negative if they were rude, unhelpful, or you learned something concerning
   - Near zero if it was unremarkable
3. OBSERVATION: One specific thing you noticed or learned about {other.name} that you want to remember (their interests, personality quirks, opinions, something they mentioned about their life, how they made you feel, etc.)

Format your response EXACTLY like this:
SUMMARY: [your summary]
FEELING: [number between -0.3 and 0.3]
OBSERVATION: [specific observation to remember, or "nothing notable"]"""
