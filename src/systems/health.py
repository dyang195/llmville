"""Health regeneration system."""

import config
from ..entities.entity_manager import EntityManager


class HealthSystem:
    """Handles health regeneration for entities."""

    def __init__(self, entity_manager: EntityManager):
        self.entity_manager = entity_manager
        self.regen_rate = config.HEALTH_REGEN_RATE

    def update(self, dt: float, time_scale: float):
        """Update health regeneration for all entities."""
        # Convert real-time dt to game minutes
        game_minutes = dt * time_scale

        for entity in self.entity_manager.get_all_entities():
            if entity.health < entity.max_health:
                # Regenerate health
                regen_amount = self.regen_rate * game_minutes
                entity.heal(regen_amount)
