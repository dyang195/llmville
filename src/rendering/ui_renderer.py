"""UI rendering (HUD, panels)."""

import pygame

import config
from ..core.time_manager import TimeManager
from ..entities.person import Person


class UIRenderer:
    """Renders HUD and UI panels."""

    def __init__(self, screen: pygame.Surface, time_manager: TimeManager):
        self.screen = screen
        self.time_manager = time_manager

        # Fonts
        pygame.font.init()
        self.font_large = pygame.font.Font(None, 36)
        self.font_medium = pygame.font.Font(None, 28)
        self.font_small = pygame.font.Font(None, 22)
        self.font_announcement = pygame.font.Font(None, 32)  # For centered announcements

        # UI state
        self.show_help = True

        # Expand button bounds (for click detection)
        self.expand_button_rect = None

    def render(self, selected_entity: Person = None, zoom: float = 1.0):
        """Render all UI elements."""
        self._render_time_display()
        self._render_zoom_indicator(zoom)
        self._render_help_text()

        if selected_entity:
            self._render_entity_panel(selected_entity)

    def _render_zoom_indicator(self, zoom: float):
        """Render zoom level indicator with background."""
        zoom_text = f"Zoom: {int(zoom * 100)}%"
        zoom_surface = self.font_small.render(zoom_text, True, (200, 200, 200))

        # Add semi-transparent background
        padding = 4
        bg_width = zoom_surface.get_width() + padding * 2
        bg_height = zoom_surface.get_height() + padding * 2
        bg_surface = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 160))

        self.screen.blit(bg_surface, (168 - padding, 16 - padding))
        self.screen.blit(zoom_surface, (168, 16))

    def _render_time_display(self):
        """Render time and day display."""
        # Background
        pygame.draw.rect(
            self.screen,
            config.COLORS["ui_background"],
            (10, 10, 150, 60),
            border_radius=5
        )
        pygame.draw.rect(
            self.screen,
            config.COLORS["ui_border"],
            (10, 10, 150, 60),
            2,
            border_radius=5
        )

        # Day
        day_text = f"Day {self.time_manager.day}"
        day_surface = self.font_medium.render(day_text, True, config.COLORS["text"])
        self.screen.blit(day_surface, (20, 18))

        # Time
        time_text = self.time_manager.get_time_string()
        time_of_day = self.time_manager.get_time_of_day()
        full_time = f"{time_text} ({time_of_day})"
        time_surface = self.font_small.render(full_time, True, config.COLORS["text_dim"])
        self.screen.blit(time_surface, (20, 42))

    def _render_help_text(self):
        """Render help text with background for readability."""
        if not self.show_help:
            return

        help_lines = [
            "WASD/Arrows: Move camera",
            "Scroll/+/-: Zoom in/out",
            "Click: Select entity",
            "Tab: Character details",
            "Space: Pause",
        ]

        # Calculate background size
        padding = 8
        line_height = 20
        max_width = max(self.font_small.size(line)[0] for line in help_lines)
        bg_height = len(help_lines) * line_height + padding * 2
        bg_width = max_width + padding * 2

        y_start = config.WINDOW_HEIGHT - 15 - len(help_lines) * line_height
        bg_rect = pygame.Rect(5, y_start - padding, bg_width, bg_height)

        # Semi-transparent background
        bg_surface = pygame.Surface((bg_width, bg_height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 160))
        self.screen.blit(bg_surface, (5, y_start - padding))

        # Render text
        y = y_start
        for line in help_lines:
            text = self.font_small.render(line, True, (200, 200, 200))
            self.screen.blit(text, (10, y))
            y += line_height

    def _render_entity_panel(self, entity: Person):
        """Render selected entity info panel."""
        panel_width = 320
        panel_height = 420
        panel_x = config.WINDOW_WIDTH - panel_width - 10
        panel_y = 10

        # Background
        pygame.draw.rect(
            self.screen,
            config.COLORS["ui_background"],
            (panel_x, panel_y, panel_width, panel_height),
            border_radius=5
        )
        pygame.draw.rect(
            self.screen,
            config.COLORS["ui_border"],
            (panel_x, panel_y, panel_width, panel_height),
            2,
            border_radius=5
        )

        # Expand button (top right corner)
        btn_size = 28
        btn_x = panel_x + panel_width - btn_size - 8
        btn_y = panel_y + 8
        self.expand_button_rect = pygame.Rect(btn_x, btn_y, btn_size, btn_size)

        # Button background
        pygame.draw.rect(
            self.screen,
            (60, 60, 80),
            self.expand_button_rect,
            border_radius=4
        )
        # Button icon (expand)
        expand_text = self.font_small.render("[+]", True, (180, 180, 200))
        text_rect = expand_text.get_rect(center=self.expand_button_rect.center)
        self.screen.blit(expand_text, text_rect)

        # Content
        x = panel_x + 15
        y = panel_y + 15

        # Name
        name_text = self.font_large.render(entity.name, True, config.COLORS["text"])
        self.screen.blit(name_text, (x, y))
        y += 35

        # Role
        role_text = f"{entity.role.role_type.value.title()}, Age {entity.age}"
        role_surface = self.font_small.render(role_text, True, config.COLORS["text_dim"])
        self.screen.blit(role_surface, (x, y))
        y += 25

        # Stats
        self._render_stat_bar(x, y, "Health", entity.health, entity.max_health, (100, 200, 100))
        y += 25

        money_text = f"Money: {entity.money:.0f} gold"
        money_surface = self.font_small.render(money_text, True, config.COLORS["text"])
        self.screen.blit(money_surface, (x, y))
        y += 25

        # Conditions (injuries/states)
        if entity.state.health_conditions:
            conditions_text = ", ".join(entity.state.health_conditions[:3])
            if len(entity.state.health_conditions) > 3:
                conditions_text += f" (+{len(entity.state.health_conditions) - 3})"
            # Use orange/red color for injuries
            condition_color = (255, 150, 100)
            cond_surface = self.font_small.render(f"⚠ {conditions_text}", True, condition_color)
            self.screen.blit(cond_surface, (x, y))
            y += 22

        # Status
        if entity.in_conversation:
            status_text = "Status: In conversation"
            status_color = config.COLORS["entity_talking"]
        elif entity.current_path:
            status_text = "Status: Walking"
            status_color = config.COLORS["text"]
        else:
            status_text = "Status: Idle"
            status_color = config.COLORS["text_dim"]

        status_surface = self.font_small.render(status_text, True, status_color)
        self.screen.blit(status_surface, (x, y))
        y += 30

        # Personality
        y = self._render_section_header(x, y, "Personality")
        trait_text = entity.personality.speech_style.title() + " speaker"
        trait_surface = self.font_small.render(trait_text, True, config.COLORS["text_dim"])
        self.screen.blit(trait_surface, (x, y))
        y += 20

        # Top trait
        if entity.personality.traits:
            top_trait = max(entity.personality.traits, key=entity.personality.traits.get)
            trait_val = entity.personality.traits[top_trait]
            trait_desc = f"Very {top_trait}" if trait_val > 0.7 else f"Somewhat {top_trait}"
            trait_surface = self.font_small.render(trait_desc, True, config.COLORS["text_dim"])
            self.screen.blit(trait_surface, (x, y))
        y += 25

        # Inventory
        y = self._render_section_header(x, y, "Inventory")
        inv_text = entity.get_inventory_string()
        if len(inv_text) > 35:
            inv_text = inv_text[:32] + "..."
        inv_surface = self.font_small.render(inv_text, True, config.COLORS["text_dim"])
        self.screen.blit(inv_surface, (x, y))
        y += 25

        # Relationships
        y = self._render_section_header(x, y, "Relationships")
        if entity.relationships:
            for rel_id, rel in list(entity.relationships.items())[:3]:
                # Show name and feeling (safely handle empty names)
                display_name = rel.entity_name.split()[0] if rel.entity_name else "Unknown"
                name_text = f"{display_name}: {rel.get_feeling_description()}"
                name_surface = self.font_small.render(name_text, True, config.COLORS["text"])
                self.screen.blit(name_surface, (x, y))
                y += 18

                # Show latest note if available
                if rel.notes:
                    note = rel.notes[-1]
                    if len(note) > 35:
                        note = note[:32] + "..."
                    note_surface = self.font_small.render(f"  \"{note}\"", True, config.COLORS["text_dim"])
                    self.screen.blit(note_surface, (x, y))
                    y += 18
        else:
            no_rel = self.font_small.render("No relationships yet", True, config.COLORS["text_dim"])
            self.screen.blit(no_rel, (x, y))

    def _render_stat_bar(
        self,
        x: int, y: int,
        label: str,
        value: float,
        max_value: float,
        color: tuple[int, int, int]
    ):
        """Render a stat bar with label."""
        bar_width = 150
        bar_height = 12

        # Label
        label_text = f"{label}: {value:.0f}/{max_value:.0f}"
        label_surface = self.font_small.render(label_text, True, config.COLORS["text"])
        self.screen.blit(label_surface, (x, y))

        # Bar background
        bar_x = x + 120
        pygame.draw.rect(
            self.screen,
            (50, 50, 50),
            (bar_x, y + 2, bar_width, bar_height),
            border_radius=3
        )

        # Bar fill
        fill_width = int((value / max_value) * bar_width)
        if fill_width > 0:
            pygame.draw.rect(
                self.screen,
                color,
                (bar_x, y + 2, fill_width, bar_height),
                border_radius=3
            )

    def _render_section_header(self, x: int, y: int, title: str) -> int:
        """Render a section header and return new y position."""
        header = self.font_medium.render(title, True, config.COLORS["text"])
        self.screen.blit(header, (x, y))
        return y + 22

    def is_expand_button_clicked(self, x: int, y: int) -> bool:
        """Check if a click hit the expand button."""
        if self.expand_button_rect:
            return self.expand_button_rect.collidepoint(x, y)
        return False
