"""Entity rendering."""

import pygame
import math
import random

import config
from ..entities.entity_manager import EntityManager
from ..entities.person import Person
from .asset_manager import get_asset_manager


class EntityRenderer:
    """Renders entities on the grid."""

    def __init__(self, screen: pygame.Surface, entity_manager: EntityManager):
        self.screen = screen
        self.entity_manager = entity_manager
        self.asset_manager = get_asset_manager()

        # Animation state
        self.glow_phase = 0.0
        self.anim_time = 0.0  # Global animation timer

    def render(self, camera_offset: tuple[float, float], tile_size: int, selected_entity: Person = None):
        """Render all entities."""
        offset_x, offset_y = camera_offset

        # Update animation timers
        self.glow_phase += 0.1
        if self.glow_phase > math.pi * 2:
            self.glow_phase -= math.pi * 2
        self.anim_time += 0.016  # ~60fps

        for entity in self.entity_manager.get_all_entities():
            self._render_entity(entity, offset_x, offset_y, tile_size, selected_entity)

    def _render_entity(
        self,
        entity: Person,
        offset_x: float,
        offset_y: float,
        tile_size: int,
        selected_entity: Person
    ):
        """Render a single entity."""
        # Get interpolated position for smooth movement
        render_x, render_y = entity.get_render_position()

        # Convert to screen coordinates
        screen_x = int(render_x * tile_size - offset_x)
        screen_y = int(render_y * tile_size - offset_y)

        # Check if on screen
        if not self._is_on_screen(screen_x, screen_y, tile_size):
            return

        center_x = screen_x + tile_size // 2
        center_y = screen_y + tile_size // 2
        entity_size = max(8, tile_size - 8)

        # Draw conversation indicator (speech bubble) if in conversation
        if entity.in_conversation:
            self._draw_speech_bubble(center_x, center_y - entity_size // 2 - 10, tile_size)

        # Draw selection highlight
        if entity == selected_entity:
            pygame.draw.circle(
                self.screen,
                config.COLORS["highlight"],
                (center_x, center_y),
                entity_size // 2 + 4,
                3
            )

        # Try to draw sprite, fallback to circle
        sprite = self._get_entity_sprite(entity, tile_size)
        if sprite:
            # Apply tint if in conversation
            if entity.in_conversation:
                glow_intensity = (math.sin(self.glow_phase) + 1) / 2
                sprite = self._apply_tint(sprite, (255, 200, 200), glow_intensity * 0.3)

            sprite_rect = sprite.get_rect(center=(center_x, center_y))
            self.screen.blit(sprite, sprite_rect)
        else:
            # Fallback: Draw colored circle
            if entity.in_conversation:
                glow_intensity = (math.sin(self.glow_phase) + 1) / 2
                base_color = config.COLORS["entity_talking"]
                color = self._blend_colors(base_color, (255, 255, 255), glow_intensity * 0.3)
            else:
                color = config.COLORS["entity"]

            pygame.draw.circle(
                self.screen,
                color,
                (center_x, center_y),
                entity_size // 2
            )

        # Draw name label (only if zoomed in enough)
        if tile_size >= 24:
            self._draw_name_label(entity.name, center_x, screen_y - 5, tile_size)

    def _get_entity_sprite(self, entity: Person, tile_size: int) -> pygame.Surface:
        """Get the sprite for an entity, with animation if moving."""
        # Assign character sprite set if not already assigned
        gender = "female" if hash(entity.name) % 2 == 0 else "male"
        self.asset_manager.assign_entity_character(entity.id, gender)

        # Check if entity is moving (has path and progress > 0)
        is_moving = bool(entity.current_path) and entity.move_progress > 0

        # Get directional sprite with animation
        sprite = self.asset_manager.get_entity_sprite(
            entity.id,
            entity.facing_direction,
            tile_size,
            is_moving=is_moving,
            anim_time=self.anim_time
        )

        return sprite

    def _apply_tint(self, surface: pygame.Surface, tint_color: tuple, intensity: float) -> pygame.Surface:
        """Apply a color tint to a surface."""
        tinted = surface.copy()
        tint_surface = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
        tint_surface.fill((*tint_color, int(255 * intensity)))
        tinted.blit(tint_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return tinted

    def _draw_speech_bubble(self, x: int, y: int, tile_size: int):
        """Draw a speech bubble indicator."""
        # Scale bubble with zoom
        scale = max(0.5, tile_size / 32)
        bubble_color = (255, 255, 255)

        width = int(20 * scale)
        height = int(12 * scale)

        pygame.draw.ellipse(
            self.screen,
            bubble_color,
            (x - width // 2, y - height, width, height)
        )
        # Small triangle pointer
        tri_size = int(5 * scale)
        points = [(x - tri_size, y), (x + tri_size, y), (x, y + tri_size)]
        pygame.draw.polygon(self.screen, bubble_color, points)

    def _draw_name_label(self, name: str, center_x: int, y: int, tile_size: int):
        """Draw entity name above them."""
        # Scale font with zoom
        font_size = max(14, min(24, int(20 * tile_size / 32)))
        font = pygame.font.Font(None, font_size)
        # Just show first name for brevity
        first_name = name.split()[0]
        text = font.render(first_name, True, config.COLORS["text"])
        text_rect = text.get_rect(center=(center_x, y))
        self.screen.blit(text, text_rect)

    def _is_on_screen(self, screen_x: int, screen_y: int, tile_size: int) -> bool:
        """Check if position is visible on screen."""
        margin = tile_size
        return (
            -margin < screen_x < config.WINDOW_WIDTH + margin and
            -margin < screen_y < config.WINDOW_HEIGHT + margin
        )

    def _blend_colors(
        self,
        color1: tuple[int, int, int],
        color2: tuple[int, int, int],
        factor: float
    ) -> tuple[int, int, int]:
        """Blend two colors together."""
        return tuple(
            int(c1 + (c2 - c1) * factor)
            for c1, c2 in zip(color1, color2)
        )
