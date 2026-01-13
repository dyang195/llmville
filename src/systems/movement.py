"""Movement and pathfinding system."""

import random

import config
from ..entities.person import Person
from ..entities.entity_manager import EntityManager
from ..core.world import World


class MovementSystem:
    """Handles entity movement and pathfinding."""

    def __init__(self, world: World, entity_manager: EntityManager):
        self.world = world
        self.entity_manager = entity_manager
        self.movement_speed = config.MOVEMENT_SPEED

    def update(self, dt: float):
        """Update all entity positions."""
        for entity in self.entity_manager.get_all_entities():
            if entity.in_conversation:
                continue
            self._update_entity(entity, dt)

    def _update_entity(self, entity: Person, dt: float):
        """Update single entity's movement."""
        # If no path, maybe pick a new destination
        if not entity.current_path or entity.path_index >= len(entity.current_path):
            if random.random() < 0.01:  # 1% chance per frame to pick new destination
                self._pick_random_destination(entity)
            return

        # Update facing direction based on next tile
        if entity.path_index < len(entity.current_path):
            next_pos = entity.current_path[entity.path_index]
            entity.facing_direction = self._get_direction(entity.position, next_pos)

        # Move along path
        entity.move_progress += self.movement_speed * dt

        # Check if reached next tile
        while entity.move_progress >= 1.0 and entity.path_index < len(entity.current_path):
            entity.move_progress -= 1.0
            entity.position = entity.current_path[entity.path_index]
            entity.path_index += 1

            # Check if path complete
            if entity.path_index >= len(entity.current_path):
                entity.current_path = []
                entity.path_index = 0
                entity.move_progress = 0.0
                entity.target_position = None
                break

    def _pick_random_destination(self, entity: Person):
        """Pick a random destination for wandering."""
        # Pick a position within reasonable distance
        x, y = entity.position
        max_distance = 15

        for _ in range(10):  # Try up to 10 times
            dx = random.randint(-max_distance, max_distance)
            dy = random.randint(-max_distance, max_distance)
            target = (x + dx, y + dy)

            if self.world.is_walkable(target[0], target[1]):
                self.set_destination(entity, target)
                return

    def set_destination(self, entity: Person, destination: tuple[int, int]) -> bool:
        """Set path for entity to destination. Returns True if path found."""
        if not self.world.is_walkable(destination[0], destination[1]):
            return False

        path = self.world.find_path(entity.position, destination)
        if not path:
            return False

        entity.current_path = path[1:]  # Exclude current position
        entity.path_index = 0
        entity.move_progress = 0.0
        entity.target_position = destination
        return True

    def stop_entity(self, entity: Person):
        """Stop entity's current movement."""
        entity.current_path = []
        entity.path_index = 0
        entity.move_progress = 0.0
        entity.target_position = None

    def _get_direction(self, from_pos: tuple[int, int], to_pos: tuple[int, int]) -> str:
        """Calculate facing direction from movement between two tiles."""
        dx = to_pos[0] - from_pos[0]
        dy = to_pos[1] - from_pos[1]

        # Map dx, dy to 8 directions
        if dx == 0 and dy > 0:
            return "south"
        elif dx == 0 and dy < 0:
            return "north"
        elif dx > 0 and dy == 0:
            return "east"
        elif dx < 0 and dy == 0:
            return "west"
        elif dx > 0 and dy > 0:
            return "south-east"
        elif dx < 0 and dy > 0:
            return "south-west"
        elif dx > 0 and dy < 0:
            return "north-east"
        elif dx < 0 and dy < 0:
            return "north-west"

        return "south"  # Default
