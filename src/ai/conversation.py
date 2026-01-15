"""Conversation state machine."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import time
import re

from ..entities.person import Person


def strip_actions_from_text(text: str) -> str:
    """Remove *action* text from dialogue, keeping only spoken words.

    Example: '"Hello!" *waves hand* "How are you?"' -> '"Hello!" "How are you?"'
    """
    # Remove text between asterisks (including the asterisks)
    stripped = re.sub(r'\*[^*]+\*', '', text)
    # Clean up extra whitespace
    stripped = re.sub(r'\s+', ' ', stripped).strip()
    return stripped


class ConversationState(Enum):
    """States of a conversation."""
    STARTING = "starting"
    ACTIVE = "active"
    ENDING = "ending"
    ENDED = "ended"


@dataclass
class Message:
    """A single message in the conversation."""
    speaker_id: str
    speaker_name: str
    content: str
    timestamp: float = field(default_factory=time.time)
    actions: list = field(default_factory=list)
    is_narrator: bool = False  # True for narrator/action outcome messages


class Conversation:
    """Manages state and history of a single conversation."""

    def __init__(self, participant_a: Person, participant_b: Person):
        self.id = f"conv_{participant_a.id}_{participant_b.id}_{int(time.time())}"
        self.participant_a = participant_a
        self.participant_b = participant_b
        self.state = ConversationState.STARTING
        self.messages: list[Message] = []
        self.current_speaker: Person = participant_a  # Who speaks next
        self.turn_count = 0
        self.max_turns = 10  # Configurable
        self.started_at = time.time()

        # Track pending actions (trades, etc.)
        self.pending_trade = None

    def add_message(self, speaker: Person, content: str, actions: list = None):
        """Add a message to the conversation."""
        self.messages.append(Message(
            speaker_id=speaker.id,
            speaker_name=speaker.name,
            content=content,
            actions=actions or []
        ))
        self.turn_count += 1

        # Check if conversation should end
        if self.turn_count >= self.max_turns * 2:  # Max turns per participant
            self.state = ConversationState.ENDING

    def add_narrator_message(self, content: str):
        """Add a narrator message describing an action outcome.

        Narrator messages don't count toward turn count and are displayed
        differently in the UI.
        """
        if not content:
            return

        self.messages.append(Message(
            speaker_id="narrator",
            speaker_name="Narrator",
            content=content,
            is_narrator=True
        ))
        # Don't increment turn count for narrator messages

    def switch_speaker(self) -> Person:
        """Switch to the other speaker and return them."""
        if self.current_speaker == self.participant_a:
            self.current_speaker = self.participant_b
        else:
            self.current_speaker = self.participant_a
        return self.current_speaker

    def get_other_participant(self, speaker: Person) -> Person:
        """Get the other participant in the conversation."""
        if speaker == self.participant_a:
            return self.participant_b
        return self.participant_a

    def get_messages_for_api(self, perspective: Person) -> list[dict[str, str]]:
        """Format messages for Claude API from a participant's perspective.

        Narrator messages are included as user messages with a [Narrator] prefix
        so the AI knows what happened.
        """
        api_messages = []

        for msg in self.messages:
            if msg.is_narrator:
                # Include narrator as context in a user message
                api_messages.append({
                    "role": "user",
                    "content": f"[Narrator: {msg.content}]"
                })
            elif msg.speaker_id == perspective.id:
                # Their own messages are "assistant"
                api_messages.append({
                    "role": "assistant",
                    "content": msg.content
                })
            else:
                # Other person's messages are "user"
                api_messages.append({
                    "role": "user",
                    "content": msg.content
                })

        return api_messages

    def get_display_messages(self) -> list[dict]:
        """Get messages formatted for display.

        Dialogue messages have *actions* stripped out (those show as narrator messages).
        Narrator messages are kept as-is for inline display.
        """
        result = []
        for msg in self.messages:
            if msg.is_narrator:
                # Narrator messages display as-is
                result.append({
                    "speaker": msg.speaker_name,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                    "is_narrator": True
                })
            else:
                # Strip *actions* from dialogue display
                display_content = strip_actions_from_text(msg.content)
                # Only add if there's actual dialogue left
                if display_content:
                    result.append({
                        "speaker": msg.speaker_name,
                        "content": display_content,
                        "timestamp": msg.timestamp,
                        "is_narrator": False
                    })
        return result

    def end(self):
        """End the conversation."""
        self.state = ConversationState.ENDED

        # Clear conversation flags on participants
        self.participant_a.in_conversation = False
        self.participant_b.in_conversation = False
        self.participant_a.conversation_partner_id = None
        self.participant_b.conversation_partner_id = None

    def is_active(self) -> bool:
        """Check if conversation is still active."""
        return self.state in (ConversationState.STARTING, ConversationState.ACTIVE)
