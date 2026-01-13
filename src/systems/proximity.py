"""Proximity detection system."""

import random

import config
from ..entities.person import Person
from ..entities.entity_manager import EntityManager


class ProximitySystem:
    """Detects when entities are adjacent for potential interaction."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        # Track cooldowns: (entity_a_id, entity_b_id) -> game_time of last interaction
        self.interaction_cooldowns: dict[tuple[str, str], float] = {}
        self.cooldown_duration = config.INTERACTION_COOLDOWN

    def update(self, game_time: float) -> list[tuple[Person, Person]]:
        """Check for adjacent entities and return potential interaction pairs."""
        potential_interactions = []
        checked_pairs = set()

        for entity in self.entity_manager.get_all_entities():
            if entity.in_conversation:
                continue

            adjacent = self.entity_manager.get_adjacent_entities(entity)

            for other in adjacent:
                if other.in_conversation:
                    continue

                # Create sorted pair to avoid duplicates
                pair_key = tuple(sorted([entity.id, other.id]))
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)

                # Check cooldown
                if not self.can_interact(entity, other, game_time):
                    continue

                # Random chance to interact
                if random.random() < config.CONVERSATION_CHANCE:
                    potential_interactions.append((entity, other))

        return potential_interactions

    def can_interact(self, entity_a: Person, entity_b: Person, game_time: float) -> bool:
        """Check if two entities can initiate interaction (not on cooldown)."""
        pair_key = tuple(sorted([entity_a.id, entity_b.id]))
        last_interaction = self.interaction_cooldowns.get(pair_key, -float('inf'))
        return game_time - last_interaction >= self.cooldown_duration

    def record_interaction(self, entity_a: Person, entity_b: Person, game_time: float):
        """Record that an interaction occurred."""
        pair_key = tuple(sorted([entity_a.id, entity_b.id]))
        self.interaction_cooldowns[pair_key] = game_time

    def get_cooldown_remaining(self, entity_a: Person, entity_b: Person, game_time: float) -> float:
        """Get remaining cooldown time between two entities."""
        pair_key = tuple(sorted([entity_a.id, entity_b.id]))
        last_interaction = self.interaction_cooldowns.get(pair_key, -float('inf'))
        remaining = self.cooldown_duration - (game_time - last_interaction)
        return max(0, remaining)
