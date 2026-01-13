"""Person entity with all attributes."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random

import config
from .item import Item


class RoleType(Enum):
    """Types of roles in the town."""
    SHOPKEEPER = "shopkeeper"
    FARMER = "farmer"
    GUARD = "guard"
    VILLAGER = "villager"
    BLACKSMITH = "blacksmith"
    INNKEEPER = "innkeeper"


@dataclass
class Personality:
    """Entity personality traits and characteristics."""
    traits: dict[str, float] = field(default_factory=dict)  # 0.0 to 1.0
    background: str = ""
    speech_style: str = "casual"
    quirks: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)

    @classmethod
    def generate_random(cls, name: str, role: str) -> "Personality":
        """Generate a random personality."""
        traits = {trait: random.random() for trait in config.PERSONALITY_TRAITS}

        backgrounds = [
            f"{name} grew up in this town and knows everyone.",
            f"{name} arrived from a distant land seeking opportunity.",
            f"{name} inherited their trade from their parents.",
            f"{name} was once a traveler who decided to settle down.",
            f"{name} has lived here all their life and loves the simple ways.",
        ]

        quirks_pool = [
            "Always mentions the weather",
            "Uses food metaphors constantly",
            "Sighs dramatically when thinking",
            "Speaks in short, clipped sentences",
            "Tends to repeat the last thing they heard",
            "Often looks around nervously",
            "Laughs at their own observations",
            "Frequently mentions their family",
        ]

        goals_by_role = {
            "shopkeeper": ["Make profitable trades", "Build a loyal customer base"],
            "farmer": ["Have a good harvest", "Sell crops at fair prices"],
            "guard": ["Keep the peace", "Protect the townspeople"],
            "villager": ["Live a peaceful life", "Help neighbors when needed"],
            "blacksmith": ["Craft quality goods", "Find rare materials"],
            "innkeeper": ["Keep guests happy", "Hear interesting stories"],
        }

        return cls(
            traits=traits,
            background=random.choice(backgrounds),
            speech_style=random.choice(config.SPEECH_STYLES),
            quirks=random.sample(quirks_pool, k=random.randint(1, 2)),
            goals=goals_by_role.get(role, ["Live a good life"])
        )


@dataclass
class Relationship:
    """Relationship with another entity."""
    entity_id: str
    entity_name: str
    feeling_score: float = 0.0  # -1.0 to 1.0
    interaction_count: int = 0
    last_interaction: float = 0.0  # Game time of last interaction
    history: list[str] = field(default_factory=list)  # Summaries of past conversations
    notes: list[str] = field(default_factory=list)  # Memorable details

    def get_feeling_description(self) -> str:
        """Get a short feeling label."""
        if self.feeling_score > 0.5:
            return "close friend"
        elif self.feeling_score > 0.2:
            return "friendly"
        elif self.feeling_score > -0.2:
            return "neutral"
        elif self.feeling_score > -0.5:
            return "wary"
        else:
            return "hostile"

    def get_display_summary(self) -> str:
        """Get a rich description including notes for UI display."""
        feeling = self.get_feeling_description()

        # If we have notes, show the most recent one
        if self.notes:
            latest_note = self.notes[-1]
            # Truncate if too long
            if len(latest_note) > 40:
                latest_note = latest_note[:37] + "..."
            return f"{feeling} - {latest_note}"

        return feeling


@dataclass
class Role:
    """Entity's role in the town."""
    role_type: RoleType
    workplace_id: Optional[str] = None
    schedule: dict[str, tuple[int, int]] = field(default_factory=dict)

    @classmethod
    def create(cls, role_type: RoleType, workplace_id: Optional[str] = None) -> "Role":
        """Create a role with default schedule."""
        schedules = {
            RoleType.SHOPKEEPER: {
                "morning": "workplace",
                "afternoon": "workplace",
                "evening": "home",
                "night": "home",
            },
            RoleType.FARMER: {
                "morning": "workplace",
                "afternoon": "workplace",
                "evening": "tavern",
                "night": "home",
            },
            RoleType.GUARD: {
                "morning": "patrol",
                "afternoon": "patrol",
                "evening": "patrol",
                "night": "home",
            },
        }
        return cls(
            role_type=role_type,
            workplace_id=workplace_id,
            schedule=schedules.get(role_type, {})
        )


@dataclass
class InventorySlot:
    """A slot in the inventory holding an item and quantity."""
    item: Item
    quantity: int = 1


class Person:
    """A person entity in the simulation."""

    def __init__(
        self,
        entity_id: str,
        name: str,
        position: tuple[int, int] = (0, 0),
        role_type: RoleType = RoleType.VILLAGER,
    ):
        self.id = entity_id
        self.name = name

        # Position and movement
        self.position = position
        self.target_position: Optional[tuple[int, int]] = None
        self.current_path: list[tuple[int, int]] = []
        self.path_index: int = 0
        self.move_progress: float = 0.0  # 0.0 to 1.0 between tiles

        # Stats
        self.health = config.DEFAULT_HEALTH
        self.max_health = config.DEFAULT_HEALTH
        self.money = config.DEFAULT_MONEY + random.uniform(-20, 30)
        self.age = random.randint(18, 65)

        # Inventory
        self.inventory: list[InventorySlot] = []
        self.inventory_capacity = config.INVENTORY_CAPACITY

        # Personality and role
        self.personality = Personality.generate_random(name, role_type.value)
        self.role = Role.create(role_type)

        # Relationships
        self.relationships: dict[str, Relationship] = {}

        # State
        self.in_conversation: bool = False
        self.conversation_partner_id: Optional[str] = None
        self.facing_direction: str = "south"  # Default facing direction

    def get_grid_position(self) -> tuple[int, int]:
        """Get current grid position."""
        return self.position

    def get_render_position(self) -> tuple[float, float]:
        """Get interpolated position for smooth rendering."""
        if not self.current_path or self.path_index >= len(self.current_path):
            return (float(self.position[0]), float(self.position[1]))

        current = self.position
        next_pos = self.current_path[self.path_index]

        x = current[0] + (next_pos[0] - current[0]) * self.move_progress
        y = current[1] + (next_pos[1] - current[1]) * self.move_progress
        return (x, y)

    def add_item(self, item: Item, quantity: int = 1) -> bool:
        """Add item to inventory. Returns True if successful."""
        # Check if item already exists and is stackable
        for slot in self.inventory:
            if slot.item.id == item.id and item.stackable:
                if slot.quantity + quantity <= item.max_stack:
                    slot.quantity += quantity
                    return True

        # Check capacity
        if len(self.inventory) >= self.inventory_capacity:
            return False

        # Add new slot
        self.inventory.append(InventorySlot(item=item, quantity=quantity))
        return True

    def remove_item(self, item_id: str, quantity: int = 1) -> bool:
        """Remove item from inventory. Returns True if successful."""
        for i, slot in enumerate(self.inventory):
            if slot.item.id == item_id:
                if slot.quantity >= quantity:
                    slot.quantity -= quantity
                    if slot.quantity <= 0:
                        self.inventory.pop(i)
                    return True
        return False

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        """Check if entity has item in inventory."""
        for slot in self.inventory:
            if slot.item.id == item_id and slot.quantity >= quantity:
                return True
        return False

    def get_item_count(self, item_id: str) -> int:
        """Get quantity of item in inventory."""
        for slot in self.inventory:
            if slot.item.id == item_id:
                return slot.quantity
        return 0

    def get_relationship(self, other_id: str, other_name: str = "") -> Relationship:
        """Get or create relationship with another entity."""
        if other_id not in self.relationships:
            self.relationships[other_id] = Relationship(
                entity_id=other_id,
                entity_name=other_name
            )
        return self.relationships[other_id]

    def update_relationship(
        self,
        other_id: str,
        feeling_delta: float,
        note: Optional[str] = None,
        summary: Optional[str] = None,
        game_time: float = 0.0
    ):
        """Update relationship after interaction."""
        rel = self.get_relationship(other_id)
        rel.feeling_score = max(-1.0, min(1.0, rel.feeling_score + feeling_delta))
        rel.interaction_count += 1
        rel.last_interaction = game_time

        if note:
            rel.notes.append(note)
            # Keep only last 5 notes
            rel.notes = rel.notes[-5:]

        if summary:
            rel.history.append(summary)
            # Keep only last 10 summaries
            rel.history = rel.history[-10:]

    def get_inventory_string(self) -> str:
        """Get string representation of inventory."""
        if not self.inventory:
            return "Empty"
        return ", ".join(
            f"{slot.item.name} x{slot.quantity}" if slot.quantity > 1 else slot.item.name
            for slot in self.inventory
        )

    def take_damage(self, amount: float):
        """Take damage."""
        self.health = max(0, self.health - amount)

    def heal(self, amount: float):
        """Heal health."""
        self.health = min(self.max_health, self.health + amount)

    def is_alive(self) -> bool:
        """Check if entity is alive."""
        return self.health > 0


# Name pools for generation
FIRST_NAMES = [
    "Ada", "Marcus", "Elena", "Thomas", "Maria", "John", "Sarah", "William",
    "Emma", "James", "Olivia", "Henry", "Sophia", "George", "Isabella", "Edward",
    "Mia", "Arthur", "Charlotte", "Frederick", "Amelia", "Albert", "Grace", "Harold"
]

LAST_NAMES = [
    "Smith", "Cooper", "Fletcher", "Miller", "Baker", "Thatcher", "Mason",
    "Wright", "Taylor", "Ward", "Cook", "Stone", "Rivers", "Woods", "Hill"
]


def generate_random_name() -> str:
    """Generate a random full name."""
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
