"""Expanded character detail panel."""

import pygame
from typing import Optional

import config
from ..entities.person import Person
from ..entities.entity_manager import EntityManager


class CharacterPanel:
    """Full-screen character detail panel with navigation."""

    def __init__(self, screen: pygame.Surface, entity_manager: EntityManager):
        self.screen = screen
        self.entity_manager = entity_manager
        self.visible = False
        self.current_entity: Optional[Person] = None
        self.entity_index = 0  # For cycling through entities

        # Panel dimensions (large, centered)
        self.margin = 50
        self.width = config.WINDOW_WIDTH - self.margin * 2
        self.height = config.WINDOW_HEIGHT - self.margin * 2
        self.x = self.margin
        self.y = self.margin

        # Colors
        self.bg_color = (25, 25, 35)
        self.border_color = (80, 80, 100)
        self.section_bg = (35, 35, 50)
        self.text_color = (240, 240, 240)
        self.dim_color = (150, 150, 170)
        self.highlight_color = (100, 200, 255)
        self.warning_color = (255, 150, 100)

        # Fonts
        pygame.font.init()
        self.font_title = pygame.font.Font(None, 48)
        self.font_header = pygame.font.Font(None, 32)
        self.font_body = pygame.font.Font(None, 24)
        self.font_small = pygame.font.Font(None, 20)

    def show(self, entity: Person = None):
        """Show the panel, optionally with a specific entity."""
        self.visible = True
        if entity:
            self.current_entity = entity
            # Find index
            entities = self.entity_manager.get_all_entities()
            for i, e in enumerate(entities):
                if e.id == entity.id:
                    self.entity_index = i
                    break
        elif not self.current_entity:
            entities = self.entity_manager.get_all_entities()
            if entities:
                self.current_entity = entities[0]
                self.entity_index = 0

    def hide(self):
        """Hide the panel."""
        self.visible = False

    def toggle(self, entity: Person = None):
        """Toggle panel visibility."""
        if self.visible:
            self.hide()
        else:
            self.show(entity)

    def next_entity(self):
        """Cycle to next entity."""
        entities = self.entity_manager.get_all_entities()
        if entities:
            self.entity_index = (self.entity_index + 1) % len(entities)
            self.current_entity = entities[self.entity_index]

    def prev_entity(self):
        """Cycle to previous entity."""
        entities = self.entity_manager.get_all_entities()
        if entities:
            self.entity_index = (self.entity_index - 1) % len(entities)
            self.current_entity = entities[self.entity_index]

    def render(self):
        """Render the expanded character panel."""
        if not self.visible or not self.current_entity:
            return

        entity = self.current_entity

        # Semi-transparent overlay
        overlay = pygame.Surface((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(180)
        self.screen.blit(overlay, (0, 0))

        # Main panel
        panel_rect = pygame.Rect(self.x, self.y, self.width, self.height)
        pygame.draw.rect(self.screen, self.bg_color, panel_rect, border_radius=10)
        pygame.draw.rect(self.screen, self.border_color, panel_rect, 2, border_radius=10)

        # Navigation hint
        nav_text = "Left/Right to switch characters | ESC to close"
        nav_surface = self.font_small.render(nav_text, True, self.dim_color)
        self.screen.blit(nav_surface, (self.x + 20, self.y + self.height - 30))

        # Entity counter
        entities = self.entity_manager.get_all_entities()
        counter_text = f"{self.entity_index + 1} / {len(entities)}"
        counter_surface = self.font_small.render(counter_text, True, self.dim_color)
        self.screen.blit(counter_surface, (self.x + self.width - 80, self.y + self.height - 30))

        # Content area
        content_x = self.x + 30
        content_y = self.y + 30

        # Name and role
        name_surface = self.font_title.render(entity.name, True, self.text_color)
        self.screen.blit(name_surface, (content_x, content_y))
        content_y += 50

        role_text = f"{entity.role.role_type.value.title()}, Age {entity.age}"
        role_surface = self.font_body.render(role_text, True, self.dim_color)
        self.screen.blit(role_surface, (content_x, content_y))
        content_y += 40

        # Two-column layout
        col1_x = content_x
        col2_x = self.x + self.width // 2 + 20
        col_width = self.width // 2 - 60

        # === LEFT COLUMN ===
        left_y = content_y

        # Health section
        left_y = self._render_section(col1_x, left_y, col_width, "Health & Status", [
            ("Health", f"{entity.health:.0f} / {entity.max_health:.0f}"),
            ("Money", f"{entity.money:.0f} gold"),
            ("Status", "In conversation" if entity.in_conversation else "Walking" if entity.current_path else "Idle"),
        ])

        # Conditions section
        conditions = entity.state.health_conditions if entity.state.health_conditions else ["None"]
        left_y = self._render_list_section(col1_x, left_y, col_width, "Conditions", conditions, self.warning_color)

        # Inventory section
        inventory = []
        for slot in entity.inventory:
            inventory.append(f"{slot.item.name} x{slot.quantity}")
        if not inventory:
            inventory = ["Empty"]
        left_y = self._render_list_section(col1_x, left_y, col_width, "Inventory", inventory)

        # === RIGHT COLUMN ===
        right_y = content_y

        # Personality section
        traits = []
        for trait, value in entity.personality.traits.items():
            if value > 0.7:
                traits.append(f"Very {trait}")
            elif value > 0.5:
                traits.append(f"Somewhat {trait}")
            elif value < 0.3:
                traits.append(f"Not {trait}")
        if not traits:
            traits = ["Average"]
        traits.insert(0, f"Speech: {entity.personality.speech_style}")
        right_y = self._render_list_section(col2_x, right_y, col_width, "Personality", traits)

        # Background
        bg_lines = self._wrap_text(entity.personality.background, col_width - 20)
        right_y = self._render_list_section(col2_x, right_y, col_width, "Background", bg_lines[:4])

        # Relationships section (full)
        right_y = self._render_relationships(col2_x, right_y, col_width, entity)

    def _render_section(self, x: int, y: int, width: int, title: str, items: list) -> int:
        """Render a key-value section."""
        # Section background
        section_height = 30 + len(items) * 24
        pygame.draw.rect(self.screen, self.section_bg,
                        (x, y, width, section_height), border_radius=5)

        # Title
        title_surface = self.font_header.render(title, True, self.highlight_color)
        self.screen.blit(title_surface, (x + 10, y + 5))
        y += 32

        # Items
        for label, value in items:
            label_surface = self.font_body.render(f"{label}:", True, self.dim_color)
            self.screen.blit(label_surface, (x + 15, y))
            value_surface = self.font_body.render(str(value), True, self.text_color)
            self.screen.blit(value_surface, (x + 120, y))
            y += 24

        return y + 15

    def _render_list_section(self, x: int, y: int, width: int, title: str,
                             items: list, item_color: tuple = None) -> int:
        """Render a list section."""
        if item_color is None:
            item_color = self.text_color

        # Section background
        section_height = 30 + len(items) * 22
        pygame.draw.rect(self.screen, self.section_bg,
                        (x, y, width, section_height), border_radius=5)

        # Title
        title_surface = self.font_header.render(title, True, self.highlight_color)
        self.screen.blit(title_surface, (x + 10, y + 5))
        y += 32

        # Items
        for item in items:
            # Truncate if too long
            if len(str(item)) > 45:
                item = str(item)[:42] + "..."
            item_surface = self.font_small.render(f"• {item}", True, item_color)
            self.screen.blit(item_surface, (x + 15, y))
            y += 22

        return y + 15

    def _render_relationships(self, x: int, y: int, width: int, entity: Person) -> int:
        """Render full relationships section."""
        relationships = list(entity.relationships.items())

        if not relationships:
            return self._render_list_section(x, y, width, "Relationships", ["No relationships yet"])

        # Section background - dynamic height
        section_height = 35
        for _, rel in relationships:
            section_height += 24  # Name line
            if rel.notes:
                section_height += 54  # Up to 3 lines of note text
            section_height += 10  # Spacing

        section_height = min(section_height, 400)  # Cap height

        pygame.draw.rect(self.screen, self.section_bg,
                        (x, y, width, section_height), border_radius=5)

        # Title
        title_surface = self.font_header.render("Relationships", True, self.highlight_color)
        self.screen.blit(title_surface, (x + 10, y + 5))
        y += 35

        # Each relationship
        for rel_id, rel in relationships[:6]:  # Max 6
            display_name = rel.entity_name.split()[0] if rel.entity_name else "Unknown"
            feeling = rel.get_feeling_description()

            # Color based on feeling
            if rel.feeling_score > 0.3:
                name_color = (100, 255, 100)  # Green
            elif rel.feeling_score < -0.3:
                name_color = (255, 100, 100)  # Red
            else:
                name_color = self.text_color

            name_text = f"{display_name}: {feeling} ({rel.feeling_score:+.2f})"
            name_surface = self.font_body.render(name_text, True, name_color)
            self.screen.blit(name_surface, (x + 15, y))
            y += 24

            # Latest note (wrap instead of truncate)
            if rel.notes:
                note = rel.notes[-1]
                note_lines = self._wrap_text(f'"{note}"', width - 40)
                for note_line in note_lines[:3]:  # Max 3 lines per note
                    note_surface = self.font_small.render(f'  {note_line}', True, self.dim_color)
                    self.screen.blit(note_surface, (x + 20, y))
                    y += 18

            y += 5

        return y + 10

    def _wrap_text(self, text: str, max_width: int) -> list:
        """Wrap text to fit within width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)
            if self.font_small.size(test_line)[0] > max_width:
                if len(current_line) > 1:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(test_line)
                    current_line = []

        if current_line:
            lines.append(' '.join(current_line))

        return lines
