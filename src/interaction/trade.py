"""Trading mechanics."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from ..entities.person import Person
from ..entities.item import Item


class TradeResult(Enum):
    """Result of a trade attempt."""
    SUCCESS = "success"
    REJECTED = "rejected"
    INVALID = "invalid"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    INSUFFICIENT_ITEMS = "insufficient_items"


@dataclass
class TradeOffer:
    """A trade offer between two entities."""
    offerer_id: str
    receiver_id: str
    offered_item_id: Optional[str]  # None if offering gold
    offered_quantity: int
    offered_gold: float
    requested_item_id: Optional[str]  # None if requesting gold
    requested_quantity: int
    requested_gold: float


class Trade:
    """Handles trade logic between entities."""

    @staticmethod
    def validate_trade(
        offerer: Person,
        receiver: Person,
        offer: TradeOffer
    ) -> tuple[bool, str]:
        """Validate if a trade is possible.

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check offerer has what they're offering
        if offer.offered_item_id:
            if not offerer.has_item(offer.offered_item_id, offer.offered_quantity):
                return False, f"{offerer.name} doesn't have enough {offer.offered_item_id}"

        if offer.offered_gold > 0:
            if offerer.money < offer.offered_gold:
                return False, f"{offerer.name} doesn't have enough gold"

        # Check receiver has what's requested
        if offer.requested_item_id:
            if not receiver.has_item(offer.requested_item_id, offer.requested_quantity):
                return False, f"{receiver.name} doesn't have enough {offer.requested_item_id}"

        if offer.requested_gold > 0:
            if receiver.money < offer.requested_gold:
                return False, f"{receiver.name} doesn't have enough gold"

        return True, "Trade is valid"

    @staticmethod
    def execute_trade(
        offerer: Person,
        receiver: Person,
        offer: TradeOffer
    ) -> TradeResult:
        """Execute a validated trade."""
        is_valid, reason = Trade.validate_trade(offerer, receiver, offer)
        if not is_valid:
            return TradeResult.INVALID

        # Transfer offered items/gold from offerer to receiver
        if offer.offered_item_id:
            offerer.remove_item(offer.offered_item_id, offer.offered_quantity)
            from ..entities.item import get_item
            item = get_item(offer.offered_item_id)
            if item:
                receiver.add_item(item, offer.offered_quantity)

        if offer.offered_gold > 0:
            offerer.money -= offer.offered_gold
            receiver.money += offer.offered_gold

        # Transfer requested items/gold from receiver to offerer
        if offer.requested_item_id:
            receiver.remove_item(offer.requested_item_id, offer.requested_quantity)
            from ..entities.item import get_item
            item = get_item(offer.requested_item_id)
            if item:
                offerer.add_item(item, offer.requested_quantity)

        if offer.requested_gold > 0:
            receiver.money -= offer.requested_gold
            offerer.money += offer.requested_gold

        return TradeResult.SUCCESS

    @staticmethod
    def calculate_fair_value(item: Item, seller: Person, buyer: Person) -> float:
        """Calculate a fair price for an item based on seller's greed and buyer's relationship."""
        base_price = item.base_value

        # Seller's greed increases price
        seller_greed = seller.personality.traits.get("greed", 0.5)
        greed_modifier = 1.0 + (seller_greed - 0.5) * 0.4  # 0.8 to 1.2

        # Relationship affects price (good relationship = discount)
        relationship_modifier = 1.0
        if buyer.id in seller.relationships:
            feeling = seller.relationships[buyer.id].feeling_score
            relationship_modifier = 1.0 - (feeling * 0.2)  # 0.8 to 1.2

        return base_price * greed_modifier * relationship_modifier
