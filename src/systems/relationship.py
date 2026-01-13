"""Relationship tracking system."""

from ..entities.person import Person
from ..entities.entity_manager import EntityManager


class RelationshipSystem:
    """Manages relationship updates and decay."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        self.decay_rate = 0.001  # Per game hour without interaction

    def update_from_conversation(
        self,
        entity_a: Person,
        entity_b: Person,
        feeling_delta_a: float,
        feeling_delta_b: float,
        summary: str,
        note_a: str = None,
        note_b: str = None,
        game_time: float = 0.0
    ):
        """Update both participants' relationships after conversation."""
        entity_a.update_relationship(
            other_id=entity_b.id,
            feeling_delta=feeling_delta_a,
            note=note_a,
            summary=summary,
            game_time=game_time
        )
        # Ensure the name is set
        entity_a.relationships[entity_b.id].entity_name = entity_b.name

        entity_b.update_relationship(
            other_id=entity_a.id,
            feeling_delta=feeling_delta_b,
            note=note_b,
            summary=summary,
            game_time=game_time
        )
        entity_b.relationships[entity_a.id].entity_name = entity_a.name

    def calculate_interaction_willingness(self, entity: Person, other: Person) -> float:
        """Calculate how willing entity is to interact with other (0-1)."""
        # Base willingness from personality
        base = entity.personality.traits.get("friendliness", 0.5)

        # Modify by relationship
        if other.id in entity.relationships:
            rel = entity.relationships[other.id]
            # Positive relationships increase willingness
            # Negative relationships decrease it (but don't go below 0.1)
            relationship_modifier = rel.feeling_score * 0.3
            base = max(0.1, min(1.0, base + relationship_modifier))

        return base

    def decay_relationships(self, dt: float, time_scale: float):
        """Slowly decay relationships over time without interaction."""
        game_hours = (dt * time_scale) / 60.0

        for entity in self.entity_manager.get_all_entities():
            for rel in entity.relationships.values():
                # Decay towards neutral (0)
                if rel.feeling_score > 0:
                    rel.feeling_score = max(0, rel.feeling_score - self.decay_rate * game_hours)
                elif rel.feeling_score < 0:
                    rel.feeling_score = min(0, rel.feeling_score + self.decay_rate * game_hours)
