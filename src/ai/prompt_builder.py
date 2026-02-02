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

        # Physical state
        speaker_conditions = speaker.state.get_conditions_string()
        listener_conditions = self._get_visible_conditions(listener)

        # Movement status
        if speaker.state.effective_move_speed < 0.9:
            movement_status = "impaired"
        else:
            movement_status = "normal"

        # Conversation phase guidance
        if turn_number >= max_turns - 1:
            phase_hint = "\n\n**This conversation has been going on a while. You should wrap up and say goodbye soon.**"
        elif turn_number >= max_turns - 2:
            phase_hint = "\n\n*The conversation is winding down. Consider wrapping up naturally.*"
        else:
            phase_hint = ""

        prompt = f"""## STOP - READ BEFORE RESPONDING

DO NOT USE ASTERISKS. No *action* text. No *sighs*. No *laughs*. No *looks around*. NONE.

Output ONLY the spoken words your character says. Nothing else.

The ONLY exception: actions that change game state, placed at the very end:
- *hands over gold* *gives item* *punches* *walks away*

If you write *sighs* or *looks* or *smiles* or ANY emotion/gesture, you have FAILED.

---

## YOUR IDENTITY
You are **{speaker.name}**. Your name is {speaker.name}. You are a {speaker.role.role_type.value}.
If asked your name, say "{speaker.name}".

## Your Personality
{personality_desc}

## Your Physical State
- Health: {speaker.health:.0f}/{speaker.max_health:.0f}
- Conditions: {speaker_conditions}
- Movement: {movement_status}

## Current Situation
{time_context}
- Your money: {speaker.money:.0f} gold
- Your inventory: {inventory_desc}

## Who You're Talking To: {listener.name}
- Appears: {"healthy" if listener.health > 70 else "injured" if listener.health > 30 else "severely injured"}
- Visible conditions: {listener_conditions}

## Your Relationship with {listener.name}
{relationship_desc}

## OUTPUT FORMAT - FOLLOW THIS EXACTLY

Format: "Your spoken dialogue here." *optional action at the very end*

RULES:
1. ONLY spoken words in quotes - nothing else
2. NO *actions* in the middle of dialogue - FORBIDDEN
3. If you include an action, it goes AFTER all dialogue, at the END
4. Actions are ONLY for state changes (violence, giving items, leaving)
5. You can ONLY write actions for YOURSELF - never write what the other person does

WRONG - action in middle: "Hello!" *laughs* "How are you?"
WRONG - action interjected: *looks around* "What do you want?"
WRONG - meaningless action: "Sure thing." *nods*
WRONG - other person's action: "Deal!" *hands over gold* *gives me the bread* ← you can't make them give you bread!
WRONG - emotion action: "That's funny!" *laughs*

CORRECT - dialogue only: "Hello! How are you?"
CORRECT - dialogue only: "What do you want?"
CORRECT - with state-change at END: "Take this." *hands over bread*
CORRECT - with violence at END: "I've had enough of you!" *punches them*

STATE-CHANGING actions (ONLY these, ONLY at the end):
- *hands over 5 gold* → changes money
- *punches them in the jaw* → changes health
- *walks away* → ends conversation
- *gives them the bread* → changes inventory
- *pickpockets their coin purse* → changes inventory, changes money
- *stabs self in the leg* → changes own's health

## Conversation Style
- You are {speaker.name}
- Keep responses to 1-2 sentences
- Be natural - say goodbye when done{phase_hint}"""

        return prompt

    def _get_visible_conditions(self, person: Person) -> str:
        """Get conditions that are visible to others."""
        visible = []
        visible_keywords = ["black eye", "broken", "limp", "bandaged", "bleeding",
                           "bruised", "swollen", "cut", "wound", "scar"]

        for condition in person.state.health_conditions:
            condition_lower = condition.lower()
            if any(kw in condition_lower for kw in visible_keywords):
                visible.append(condition)

        return ", ".join(visible) if visible else "appears healthy"

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
