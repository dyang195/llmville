"""Orchestrates active conversations using background threads."""

import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Optional
import time

import config
from ..ai.claude_client import ClaudeClient
from ..ai.prompt_builder import PromptBuilder
from ..ai.conversation import Conversation, ConversationState
from ..ai.action_parser import ActionParser, ActionType
from ..entities.person import Person
from ..entities.entity_manager import EntityManager
from ..entities.item import get_item
from ..core.time_manager import TimeManager
from ..systems.relationship import RelationshipSystem
from .trade import Trade, TradeResult


class DialogueManager:
    """Orchestrates all active conversations with non-blocking API calls."""

    def __init__(
        self,
        claude_client: ClaudeClient,
        prompt_builder: PromptBuilder,
        entity_manager: EntityManager,
        time_manager: TimeManager,
        relationship_system: RelationshipSystem
    ):
        self.claude_client = claude_client
        self.prompt_builder = prompt_builder
        self.entity_manager = entity_manager
        self.time_manager = time_manager
        self.relationship_system = relationship_system
        self.action_parser = ActionParser()

        # Active conversations
        self.conversations: dict[str, Conversation] = {}

        # For UI: currently viewed conversation
        self.viewed_conversation_id: Optional[str] = None

        # Thread pool for API calls (limit concurrent requests)
        self.executor = ThreadPoolExecutor(max_workers=3)

        # Track pending API requests per conversation
        self.pending_requests: dict[str, Future] = {}

        # Cooldown between turns (seconds) - gives time to read
        self.turn_delay = 1.5
        self.last_turn_time: dict[str, float] = {}

        # Max turns before forced ending
        self.max_turns = config.MAX_CONVERSATION_TURNS

    def initiate_conversation(self, entity_a: Person, entity_b: Person) -> Conversation:
        """Start a new conversation between two entities."""
        conversation = Conversation(entity_a, entity_b)
        conversation.max_turns = self.max_turns
        self.conversations[conversation.id] = conversation
        self.last_turn_time[conversation.id] = 0

        # Set as viewed if first conversation
        if self.viewed_conversation_id is None:
            self.viewed_conversation_id = conversation.id

        # Start first turn immediately
        self._start_turn(conversation)

        return conversation

    def update(self, paused: bool = False):
        """Called each frame - check for completed API requests and start new turns.
        This is non-blocking and returns immediately.

        Args:
            paused: If True, don't process any new turns (but still check for completed requests)
        """
        current_time = time.time()

        for conv_id, conversation in list(self.conversations.items()):
            if not conversation.is_active():
                continue

            # Check if there's a pending request
            if conv_id in self.pending_requests:
                future = self.pending_requests[conv_id]
                if future.done():
                    # Request completed - process result
                    try:
                        result = future.result()
                        self._handle_turn_result(conversation, result)
                    except Exception as e:
                        print(f"API error: {e}")
                        # Add error message to conversation
                        conversation.add_message(
                            conversation.current_speaker,
                            "*trails off awkwardly*"
                        )
                        conversation.switch_speaker()

                    del self.pending_requests[conv_id]
                    self.last_turn_time[conv_id] = current_time

                    # Check if we hit max turns
                    if conversation.turn_count >= self.max_turns * 2:
                        self._force_end_conversation(conversation)
            else:
                # No pending request - maybe start a new turn (if not paused)
                if not paused:
                    time_since_last = current_time - self.last_turn_time.get(conv_id, 0)
                    if time_since_last >= self.turn_delay:
                        self._start_turn(conversation)

        # Clean up ended conversations
        self._cleanup_ended_conversations()

    def _start_turn(self, conversation: Conversation):
        """Start a new turn by submitting API request to thread pool."""
        if conversation.id in self.pending_requests:
            return  # Already has pending request

        if not conversation.is_active():
            return

        speaker = conversation.current_speaker
        listener = conversation.get_other_participant(speaker)

        # Calculate turn number for this speaker
        speaker_turn = conversation.turn_count // 2

        # Build prompt with turn information
        system_prompt = self.prompt_builder.build_conversation_prompt(
            speaker, listener, self.time_manager,
            turn_number=speaker_turn,
            max_turns=self.max_turns
        )

        # Get conversation history from speaker's perspective
        messages = conversation.get_messages_for_api(speaker)

        # If this is the first message, add a user message to prompt the greeting
        if not messages:
            messages = [{"role": "user", "content": f"*{listener.name} approaches you*"}]
            conversation.state = ConversationState.ACTIVE

        # Submit to thread pool (non-blocking)
        future = self.executor.submit(
            self.claude_client.generate_dialogue_sync,
            system_prompt,
            messages
        )
        self.pending_requests[conversation.id] = future

    def _handle_turn_result(self, conversation: Conversation, response: str):
        """Handle completed API response."""
        speaker = conversation.current_speaker
        listener = conversation.get_other_participant(speaker)

        # Parse response for actions
        clean_text, actions = self.action_parser.parse(response)

        # Add message to conversation
        conversation.add_message(speaker, clean_text, actions)

        # Process actions
        end_requested = False
        for action in actions:
            if action.action_type == ActionType.END_CONVERSATION:
                end_requested = True
            self._handle_action(conversation, speaker, listener, action)

        # Switch speaker for next turn (if not ending)
        if not end_requested:
            conversation.switch_speaker()

    def _handle_action(
        self,
        conversation: Conversation,
        speaker: Person,
        listener: Person,
        action
    ):
        """Handle a game action from dialogue."""
        if action.action_type == ActionType.END_CONVERSATION:
            conversation.state = ConversationState.ENDING
            self._end_conversation(conversation)

        elif action.action_type == ActionType.TRADE:
            self._handle_trade_offer(
                conversation, speaker, listener,
                action.data["offered"],
                action.data["requested"]
            )

        elif action.action_type == ActionType.GIFT:
            self._handle_gift(
                conversation, speaker, listener,
                action.data["item"]
            )

    def _handle_trade_offer(
        self,
        conversation: Conversation,
        offerer: Person,
        receiver: Person,
        offered_str: str,
        requested_str: str
    ):
        """Handle a trade offer."""
        offered_id, offered_qty = self.action_parser.parse_item_reference(offered_str)
        requested_id, requested_qty = self.action_parser.parse_item_reference(requested_str)

        # Validate trade
        can_trade = True

        # Check if offerer has the item
        if offered_id == 'gold':
            if offerer.money < offered_qty:
                can_trade = False
        else:
            if not offerer.has_item(offered_id, offered_qty):
                can_trade = False

        # Check if receiver has what's requested
        if can_trade:
            if requested_id == 'gold':
                if receiver.money < requested_qty:
                    can_trade = False
            else:
                if not receiver.has_item(requested_id, requested_qty):
                    can_trade = False

        # Auto-accept valid trades
        if can_trade:
            self._execute_trade(
                offerer, receiver,
                offered_id, offered_qty,
                requested_id, requested_qty
            )

    def _execute_trade(
        self,
        offerer: Person,
        receiver: Person,
        offered_id: str,
        offered_qty: int,
        requested_id: str,
        requested_qty: int
    ):
        """Execute a trade between two entities."""
        # Transfer offered item/gold
        if offered_id == 'gold':
            offerer.money -= offered_qty
            receiver.money += offered_qty
        else:
            offerer.remove_item(offered_id, offered_qty)
            item = get_item(offered_id)
            if item:
                receiver.add_item(item, offered_qty)

        # Transfer requested item/gold
        if requested_id == 'gold':
            receiver.money -= requested_qty
            offerer.money += requested_qty
        else:
            receiver.remove_item(requested_id, requested_qty)
            item = get_item(requested_id)
            if item:
                offerer.add_item(item, requested_qty)

    def _handle_gift(
        self,
        conversation: Conversation,
        giver: Person,
        receiver: Person,
        item_str: str
    ):
        """Handle giving a gift."""
        item_id, quantity = self.action_parser.parse_item_reference(item_str)

        if item_id == 'gold':
            if giver.money >= quantity:
                giver.money -= quantity
                receiver.money += quantity
        else:
            if giver.has_item(item_id, quantity):
                giver.remove_item(item_id, quantity)
                item = get_item(item_id)
                if item:
                    receiver.add_item(item, quantity)

    def _force_end_conversation(self, conversation: Conversation):
        """Force end a conversation that has gone on too long."""
        # Add a natural ending message
        conversation.add_message(
            conversation.current_speaker,
            "Well, I should get going. Take care!"
        )
        conversation.state = ConversationState.ENDING
        self._end_conversation(conversation)

    def _end_conversation(self, conversation: Conversation):
        """End a conversation and update relationships with detailed reflections."""
        # Generate reflections in background
        def generate_reflections():
            try:
                # Get conversation from each perspective
                messages_for_a = [
                    {"role": "user" if m.speaker_id != conversation.participant_a.id else "assistant",
                     "content": m.content} for m in conversation.messages
                ]
                messages_for_b = [
                    {"role": "user" if m.speaker_id != conversation.participant_b.id else "assistant",
                     "content": m.content} for m in conversation.messages
                ]

                # Generate reflection for participant A
                reflection_prompt_a = self.prompt_builder.build_reflection_prompt(
                    conversation.participant_a,
                    conversation.participant_b,
                    messages_for_a
                )
                reflection_a = self.claude_client.generate_reflection_sync(reflection_prompt_a)

                # Generate reflection for participant B
                reflection_prompt_b = self.prompt_builder.build_reflection_prompt(
                    conversation.participant_b,
                    conversation.participant_a,
                    messages_for_b
                )
                reflection_b = self.claude_client.generate_reflection_sync(reflection_prompt_b)

                # Update relationships with detailed notes
                self.relationship_system.update_from_conversation(
                    conversation.participant_a,
                    conversation.participant_b,
                    feeling_delta_a=reflection_a["delta"],
                    feeling_delta_b=reflection_b["delta"],
                    summary=reflection_a["summary"],
                    note_a=reflection_a.get("observation"),  # A's observation about B
                    note_b=reflection_b.get("observation"),  # B's observation about A
                    game_time=self.time_manager.game_time
                )
            except Exception as e:
                print(f"Reflection generation error: {e}")
                # Still update relationships with default values
                self.relationship_system.update_from_conversation(
                    conversation.participant_a,
                    conversation.participant_b,
                    feeling_delta_a=0.05,
                    feeling_delta_b=0.05,
                    summary="Had a conversation",
                    game_time=self.time_manager.game_time
                )

        self.executor.submit(generate_reflections)

        # End conversation immediately
        conversation.end()

    def _cleanup_ended_conversations(self):
        """Remove ended conversations."""
        ended = [cid for cid, conv in self.conversations.items()
                 if conv.state == ConversationState.ENDED]

        for cid in ended:
            if self.viewed_conversation_id == cid:
                self.viewed_conversation_id = None
            if cid in self.pending_requests:
                del self.pending_requests[cid]
            if cid in self.last_turn_time:
                del self.last_turn_time[cid]
            del self.conversations[cid]

    def has_active_conversations(self) -> bool:
        """Check if there are any active conversations."""
        return any(conv.is_active() for conv in self.conversations.values())

    def get_conversation_for_entity(self, entity: Person) -> Optional[Conversation]:
        """Get the conversation an entity is participating in."""
        for conv in self.conversations.values():
            if conv.participant_a.id == entity.id or conv.participant_b.id == entity.id:
                return conv
        return None

    def get_viewed_conversation(self) -> Optional[Conversation]:
        """Get the currently viewed conversation."""
        if self.viewed_conversation_id:
            return self.conversations.get(self.viewed_conversation_id)
        return None

    def view_conversation(self, conversation_id: str):
        """Set which conversation to view."""
        if conversation_id in self.conversations:
            self.viewed_conversation_id = conversation_id

    def shutdown(self):
        """Shutdown the thread pool."""
        self.executor.shutdown(wait=False)
