"""Main game class and loop."""

import pygame
import random
from typing import Optional

import config
from .world import World
from .time_manager import TimeManager
from ..entities.entity_manager import EntityManager
from ..systems.movement import MovementSystem
from ..systems.proximity import ProximitySystem
from ..systems.health import HealthSystem
from ..systems.relationship import RelationshipSystem
from ..rendering.renderer import Renderer
from ..ui.dialogue_panel import DialoguePanel


class Game:
    """Main game controller."""

    def __init__(self):
        # Initialize pygame
        pygame.init()
        pygame.display.set_caption(config.TITLE)

        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = False

        # Core systems
        self.world = World()
        self.time_manager = TimeManager()
        self.entity_manager = EntityManager(self.world)

        # Game systems
        self.movement_system = MovementSystem(self.world, self.entity_manager)
        self.proximity_system = ProximitySystem(self.entity_manager)
        self.health_system = HealthSystem(self.entity_manager)
        self.relationship_system = RelationshipSystem(self.entity_manager)

        # UI
        self.dialogue_panel = DialoguePanel(self.screen)

        # Rendering
        self.renderer = Renderer(
            self.screen,
            self.world,
            self.entity_manager,
            self.time_manager
        )

        # Dialogue manager (will be set after AI integration)
        self.dialogue_manager = None

        # Populate town
        self.entity_manager.populate_town(count=10)

    def run(self):
        """Main game loop."""
        self.running = True

        while self.running:
            dt = self.clock.tick(config.FPS) / 1000.0  # Delta time in seconds

            self.handle_events()
            self.update(dt)
            self.render()

        # Cleanup
        if self.dialogue_manager:
            self.dialogue_manager.shutdown()

        pygame.quit()

    def handle_events(self):
        """Process pygame events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.dialogue_panel.visible:
                        self.dialogue_panel.hide()
                    else:
                        self.running = False
                elif event.key == pygame.K_SPACE:
                    self.time_manager.toggle_pause()
                elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                    self.renderer.camera.zoom_in()
                elif event.key == pygame.K_MINUS:
                    self.renderer.camera.zoom_out()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self._handle_click(*event.pos)
                elif event.button == 4:  # Scroll up
                    if self.dialogue_panel.visible:
                        self.dialogue_panel.handle_scroll(-1)
                    else:
                        self.renderer.camera.zoom_in()
                elif event.button == 5:  # Scroll down
                    if self.dialogue_panel.visible:
                        self.dialogue_panel.handle_scroll(1)
                    else:
                        self.renderer.camera.zoom_out()

            elif event.type == pygame.MOUSEWHEEL:
                if self.dialogue_panel.visible:
                    self.dialogue_panel.handle_scroll(-event.y)
                else:
                    if event.y > 0:
                        self.renderer.camera.zoom_in()
                    elif event.y < 0:
                        self.renderer.camera.zoom_out()

        # Handle held keys for camera
        keys = pygame.key.get_pressed()
        dt = self.clock.get_time() / 1000.0
        self.renderer.handle_camera_input(keys, dt)

    def _handle_click(self, x: int, y: int):
        """Handle mouse click."""
        # Check if clicking inside dialogue panel
        if self.dialogue_panel.is_point_inside(x, y):
            return  # Click absorbed by panel

        # If dialogue panel is open and clicked outside, close it
        if self.dialogue_panel.visible:
            self.dialogue_panel.hide()
            return

        # Check if clicked on an entity
        entity = self.entity_manager.get_entity_at_pixel(
            x, y,
            self.renderer.camera.get_offset(),
            self.renderer.camera.get_tile_size()
        )

        if entity:
            self.renderer.selected_entity = entity

            # If entity is in conversation, show the dialogue panel
            if entity.in_conversation and self.dialogue_manager:
                conversation = self.dialogue_manager.get_conversation_for_entity(entity)
                if conversation:
                    self.dialogue_panel.show(conversation)
        else:
            self.renderer.selected_entity = None

    def update(self, dt: float):
        """Update game state."""
        # Always update dialogue manager (non-blocking)
        # Pass paused state so new turns don't start when paused
        if self.dialogue_manager:
            self.dialogue_manager.update(paused=self.time_manager.paused)

        if self.time_manager.paused:
            return

        # Update game time
        self.time_manager.update(dt)

        # Update systems
        self.movement_system.update(dt)
        self.health_system.update(dt, self.time_manager.time_scale)
        self.relationship_system.decay_relationships(dt, self.time_manager.time_scale)

        # Check for new interactions
        potential_interactions = self.proximity_system.update(self.time_manager.game_time)

        for entity_a, entity_b in potential_interactions:
            self.initiate_interaction(entity_a, entity_b)

    def initiate_interaction(self, entity_a, entity_b):
        """Start interaction between two entities."""
        # Calculate willingness
        willingness_a = self.relationship_system.calculate_interaction_willingness(
            entity_a, entity_b
        )
        willingness_b = self.relationship_system.calculate_interaction_willingness(
            entity_b, entity_a
        )

        if random.random() > willingness_a or random.random() > willingness_b:
            return

        # Record the interaction attempt
        self.proximity_system.record_interaction(
            entity_a, entity_b, self.time_manager.game_time
        )

        # Mark entities as in conversation
        entity_a.in_conversation = True
        entity_b.in_conversation = True
        entity_a.conversation_partner_id = entity_b.id
        entity_b.conversation_partner_id = entity_a.id

        # Stop their movement
        self.movement_system.stop_entity(entity_a)
        self.movement_system.stop_entity(entity_b)

        # Start conversation through dialogue manager
        if self.dialogue_manager:
            self.dialogue_manager.initiate_conversation(entity_a, entity_b)
        else:
            # Without AI, just simulate a brief "conversation"
            self._simulate_conversation(entity_a, entity_b)

    def _simulate_conversation(self, entity_a, entity_b):
        """Simulate a conversation without AI (placeholder)."""
        # Simulate some relationship change
        feeling_delta = random.uniform(-0.1, 0.2)

        self.relationship_system.update_from_conversation(
            entity_a, entity_b,
            feeling_delta_a=feeling_delta,
            feeling_delta_b=feeling_delta,
            summary=f"Had a brief chat on Day {self.time_manager.day}",
            game_time=self.time_manager.game_time
        )

        # End conversation after a delay (simulated)
        entity_a.in_conversation = False
        entity_b.in_conversation = False
        entity_a.conversation_partner_id = None
        entity_b.conversation_partner_id = None

    def render(self):
        """Render the game."""
        self.renderer.render()

        # Show pause indicator
        if self.time_manager.paused:
            font = pygame.font.Font(None, 48)
            text = font.render("PAUSED", True, (255, 255, 255))
            text_rect = text.get_rect(center=(config.WINDOW_WIDTH // 2, 50))
            self.screen.blit(text, text_rect)

        # Render dialogue panel if visible
        if self.dialogue_panel.visible:
            self.dialogue_panel.update()  # Auto-scroll to latest
            self.dialogue_panel.render()

        pygame.display.flip()

    def set_dialogue_manager(self, dialogue_manager):
        """Set the dialogue manager for AI conversations."""
        self.dialogue_manager = dialogue_manager
