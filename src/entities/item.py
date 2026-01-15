"""Item definitions."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ItemCategory(Enum):
    """Categories of items."""
    FOOD = "food"
    TOOL = "tool"
    MATERIAL = "material"
    LUXURY = "luxury"
    WEAPON = "weapon"


@dataclass
class Item:
    """An item that can be held in inventory."""
    id: str
    name: str
    description: str
    category: ItemCategory
    base_value: float
    weight: float = 1.0
    stackable: bool = True
    max_stack: int = 99
    effects: dict[str, float] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Item):
            return self.id == other.id
        return False


# Default items catalog
DEFAULT_ITEMS = {
    "bread": Item(
        id="bread",
        name="Bread",
        description="A fresh loaf of bread",
        category=ItemCategory.FOOD,
        base_value=5.0,
        effects={"health_restore": 10}
    ),
    "apple": Item(
        id="apple",
        name="Apple",
        description="A crisp red apple",
        category=ItemCategory.FOOD,
        base_value=2.0,
        effects={"health_restore": 5}
    ),
    "ale": Item(
        id="ale",
        name="Ale",
        description="A mug of frothy ale",
        category=ItemCategory.FOOD,
        base_value=8.0,
        effects={"health_restore": 3}
    ),
    "iron_ore": Item(
        id="iron_ore",
        name="Iron Ore",
        description="Raw iron ore from the mines",
        category=ItemCategory.MATERIAL,
        base_value=15.0,
    ),
    "cloth": Item(
        id="cloth",
        name="Cloth",
        description="A bolt of woven cloth",
        category=ItemCategory.MATERIAL,
        base_value=10.0,
    ),
    "sword": Item(
        id="sword",
        name="Sword",
        description="A simple iron sword",
        category=ItemCategory.WEAPON,
        base_value=50.0,
        stackable=False,
    ),
    "hammer": Item(
        id="hammer",
        name="Hammer",
        description="A blacksmith's hammer",
        category=ItemCategory.TOOL,
        base_value=25.0,
        stackable=False,
    ),
    "gold_ring": Item(
        id="gold_ring",
        name="Gold Ring",
        description="A shiny gold ring",
        category=ItemCategory.LUXURY,
        base_value=100.0,
        stackable=False,
    ),
    "wheat": Item(
        id="wheat",
        name="Wheat",
        description="A bundle of wheat",
        category=ItemCategory.MATERIAL,
        base_value=3.0,
    ),
    "rope": Item(
        id="rope",
        name="Rope",
        description="A sturdy length of rope",
        category=ItemCategory.TOOL,
        base_value=8.0,
    ),
}


def get_item(item_id: str) -> Optional[Item]:
    """Get an item by ID from the catalog (case-insensitive)."""
    # Try exact match first
    if item_id in DEFAULT_ITEMS:
        return DEFAULT_ITEMS[item_id]
    # Try lowercase
    lower_id = item_id.lower()
    if lower_id in DEFAULT_ITEMS:
        return DEFAULT_ITEMS[lower_id]
    # Try matching by name
    for item in DEFAULT_ITEMS.values():
        if item.name.lower() == lower_id:
            return item
    return None


def get_items_by_category(category: ItemCategory) -> list[Item]:
    """Get all items in a category."""
    return [item for item in DEFAULT_ITEMS.values() if item.category == category]
