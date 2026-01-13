"""Entity registry and lifecycle management."""

from typing import Optional
import random

from .person import Person, RoleType, generate_random_name
from .item import get_item, Item
from ..core.world import World


class EntityManager:
    """Manages all entities in the simulation."""

    def __init__(self, world: World):
        self.world = world
        self.entities: dict[str, Person] = {}
        self._next_id = 0

    def _generate_id(self) -> str:
        """Generate unique entity ID."""
        entity_id = f"entity_{self._next_id}"
        self._next_id += 1
        return entity_id

    def create_person(
        self,
        name: Optional[str] = None,
        position: Optional[tuple[int, int]] = None,
        role_type: Optional[RoleType] = None,
    ) -> Person:
        """Create a new person entity."""
        entity_id = self._generate_id()

        if name is None:
            name = generate_random_name()

        if position is None:
            position = self.world.get_random_walkable_position()

        if role_type is None:
            role_type = random.choice(list(RoleType))

        person = Person(
            entity_id=entity_id,
            name=name,
            position=position,
            role_type=role_type,
        )

        # Give starting inventory based on role
        self._assign_starting_inventory(person)

        self.entities[entity_id] = person
        return person

    def _assign_starting_inventory(self, person: Person):
        """Assign starting items based on role."""
        role_items = {
            RoleType.SHOPKEEPER: ["bread", "cloth", "rope"],
            RoleType.FARMER: ["wheat", "apple", "bread"],
            RoleType.GUARD: ["sword", "bread"],
            RoleType.VILLAGER: ["bread", "apple"],
            RoleType.BLACKSMITH: ["hammer", "iron_ore"],
            RoleType.INNKEEPER: ["ale", "bread", "bread"],
        }

        items = role_items.get(person.role.role_type, ["bread"])
        for item_id in items:
            item = get_item(item_id)
            if item:
                person.add_item(item)

    def get_entity(self, entity_id: str) -> Optional[Person]:
        """Get entity by ID."""
        return self.entities.get(entity_id)

    def get_all_entities(self) -> list[Person]:
        """Get all entities."""
        return list(self.entities.values())

    def get_entities_at(self, x: int, y: int) -> list[Person]:
        """Get all entities at a specific grid position."""
        return [
            entity for entity in self.entities.values()
            if entity.position == (x, y)
        ]

    def get_adjacent_entities(self, entity: Person) -> list[Person]:
        """Get entities in adjacent cells (including diagonal)."""
        x, y = entity.position
        adjacent = []

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                entities_at = self.get_entities_at(x + dx, y + dy)
                adjacent.extend(entities_at)

        return adjacent

    def get_entity_at_pixel(
        self,
        pixel_x: float,
        pixel_y: float,
        camera_offset: tuple[float, float],
        tile_size: int
    ) -> Optional[Person]:
        """Get entity at pixel position (for click detection)."""
        # Convert pixel to world position
        world_x = (pixel_x + camera_offset[0]) / tile_size
        world_y = (pixel_y + camera_offset[1]) / tile_size

        # Check all entities
        for entity in self.entities.values():
            ex, ey = entity.get_render_position()
            # Check if click is within entity bounds (1 tile)
            if ex <= world_x < ex + 1 and ey <= world_y < ey + 1:
                return entity

        return None

    def remove_entity(self, entity_id: str):
        """Remove entity from simulation."""
        if entity_id in self.entities:
            del self.entities[entity_id]

    def populate_town(self, count: int = 10):
        """Populate the town with random entities."""
        # Ensure a variety of roles
        roles = list(RoleType)

        for i in range(count):
            role = roles[i % len(roles)]
            self.create_person(role_type=role)
