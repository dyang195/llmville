"""Parse AI responses for embedded game actions."""

import re
from dataclasses import dataclass
from typing import Optional
from enum import Enum


class ActionType(Enum):
    """Types of actions that can be embedded in dialogue."""
    TRADE = "trade"
    GIFT = "gift"
    END_CONVERSATION = "end_conversation"


@dataclass
class GameAction:
    """A parsed game action from dialogue."""
    action_type: ActionType
    data: dict


class ActionParser:
    """Parse AI responses for game actions."""

    # Patterns for action detection
    TRADE_PATTERN = r'\[TRADE:\s*OFFER\s+(.+?)\s+FOR\s+(.+?)\]'
    GIFT_PATTERN = r'\[GIFT:\s*(.+?)\]'
    END_PATTERN = r'\[END_CONVERSATION\]'

    def parse(self, response: str) -> tuple[str, list[GameAction]]:
        """Extract actions and clean dialogue text.

        Returns:
            Tuple of (cleaned_text, list_of_actions)
        """
        actions = []
        clean_text = response

        # Parse trade offers
        trade_matches = re.findall(self.TRADE_PATTERN, response, re.IGNORECASE)
        for offered, requested in trade_matches:
            actions.append(GameAction(
                action_type=ActionType.TRADE,
                data={
                    "offered": offered.strip(),
                    "requested": requested.strip()
                }
            ))

        # Parse gifts
        gift_matches = re.findall(self.GIFT_PATTERN, response, re.IGNORECASE)
        for item in gift_matches:
            actions.append(GameAction(
                action_type=ActionType.GIFT,
                data={"item": item.strip()}
            ))

        # Parse end conversation
        if re.search(self.END_PATTERN, response, re.IGNORECASE):
            actions.append(GameAction(
                action_type=ActionType.END_CONVERSATION,
                data={}
            ))

        # Clean action markers from text
        clean_text = re.sub(self.TRADE_PATTERN, '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(self.GIFT_PATTERN, '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(self.END_PATTERN, '', clean_text, flags=re.IGNORECASE)

        # Clean up whitespace
        clean_text = ' '.join(clean_text.split())

        return clean_text.strip(), actions

    def parse_item_reference(self, item_string: str) -> tuple[Optional[str], int]:
        """Parse an item reference like 'bread' or '2 bread' or '50 gold'.

        Returns:
            Tuple of (item_id or 'gold', quantity)
        """
        item_string = item_string.strip().lower()

        # Check for gold
        gold_match = re.match(r'(\d+)\s*gold', item_string)
        if gold_match:
            return ('gold', int(gold_match.group(1)))

        # Check for quantity prefix
        qty_match = re.match(r'(\d+)\s+(.+)', item_string)
        if qty_match:
            quantity = int(qty_match.group(1))
            item_name = qty_match.group(2)
        else:
            quantity = 1
            item_name = item_string

        # Normalize item name to id
        item_id = item_name.replace(' ', '_').lower()

        return (item_id, quantity)
