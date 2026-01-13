"""Main rendering coordinator."""

import pygame

import config
from .world_renderer import WorldRenderer
from .entity_renderer import EntityRenderer
from .ui_renderer import UIRenderer
from .asset_manager import get_asset_manager
from ..core.world import World
from ..entities.entity_manager import EntityManager
from ..core.time_manager import TimeManager


class Camera:
    """Viewport/camera for the game world with zoom support."""

    def __init__(self, width: int, height: int):
        self.x = 0.0
        self.y = 0.0
        self.width = width
        self.height = height
        self.speed = config.CAMERA_SPEED

        # Zoom settings
        self.zoom = 1.0
        self.max_zoom = 2.0
        self.zoom_step = 0.1
        self.base_tile_size = config.TILE_SIZE

        # World bounds (set after world is known)
        self.world_width = config.GRID_WIDTH
        self.world_height = config.GRID_HEIGHT

    def get_tile_size(self) -> int:
        """Get current tile size based on zoom."""
        return int(self.base_tile_size * self.zoom)

    def set_world_bounds(self, world_width: int, world_height: int):
        """Set the world dimensions for zoom clamping."""
        self.world_width = world_width
        self.world_height = world_height

    def get_min_zoom(self) -> float:
        """Calculate minimum zoom to fit world in viewport."""
        zoom_for_width = self.width / (self.world_width * self.base_tile_size)
        zoom_for_height = self.height / (self.world_height * self.base_tile_size)
        return max(zoom_for_width, zoom_for_height)

    def zoom_in(self):
        """Zoom in (make things bigger)."""
        self.zoom = min(self.max_zoom, self.zoom + self.zoom_step)
        self._clamp_position()

    def zoom_out(self):
        """Zoom out (make things smaller), respecting world bounds."""
        min_zoom = self.get_min_zoom()
        self.zoom = max(min_zoom, self.zoom - self.zoom_step)
        self._clamp_position()

    def _clamp_position(self):
        """Clamp camera position after zoom change."""
        self.clamp_to_world(self.world_width, self.world_height)

    def move(self, dx: float, dy: float, dt: float):
        """Move camera by delta."""
        # Adjust speed based on zoom (slower when zoomed in)
        adjusted_speed = self.speed / self.zoom
        self.x += dx * adjusted_speed * dt
        self.y += dy * adjusted_speed * dt

    def center_on(self, world_x: float, world_y: float):
        """Center camera on world position."""
        tile_size = self.get_tile_size()
        self.x = world_x * tile_size - self.width / 2
        self.y = world_y * tile_size - self.height / 2

    def clamp_to_world(self, world_width: int, world_height: int):
        """Clamp camera to world bounds."""
        tile_size = self.get_tile_size()
        world_pixel_width = world_width * tile_size
        world_pixel_height = world_height * tile_size

        # If world is smaller than viewport, center it
        if world_pixel_width <= self.width:
            self.x = (world_pixel_width - self.width) / 2
        else:
            max_x = world_pixel_width - self.width
            self.x = max(0, min(max_x, self.x))

        if world_pixel_height <= self.height:
            self.y = (world_pixel_height - self.height) / 2
        else:
            max_y = world_pixel_height - self.height
            self.y = max(0, min(max_y, self.y))

    def get_offset(self) -> tuple[float, float]:
        """Get camera offset for rendering."""
        return (self.x, self.y)

    def world_to_screen(self, world_x: float, world_y: float) -> tuple[int, int]:
        """Convert world coordinates to screen coordinates."""
        tile_size = self.get_tile_size()
        screen_x = int(world_x * tile_size - self.x)
        screen_y = int(world_y * tile_size - self.y)
        return (screen_x, screen_y)

    def screen_to_world(self, screen_x: int, screen_y: int) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        tile_size = self.get_tile_size()
        world_x = (screen_x + self.x) / tile_size
        world_y = (screen_y + self.y) / tile_size
        return (world_x, world_y)


class Renderer:
    """Main rendering coordinator."""

    def __init__(
        self,
        screen: pygame.Surface,
        world: World,
        entity_manager: EntityManager,
        time_manager: TimeManager
    ):
        self.screen = screen
        self.world = world
        self.entity_manager = entity_manager
        self.time_manager = time_manager

        # Initialize camera centered on world
        self.camera = Camera(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.camera.set_world_bounds(world.width, world.height)
        self.camera.center_on(world.width / 2, world.height / 2)

        # Load assets
        self.asset_manager = get_asset_manager()
        self.asset_manager.load_all()

        # Initialize sub-renderers
        self.world_renderer = WorldRenderer(screen, world)
        self.entity_renderer = EntityRenderer(screen, entity_manager)
        self.ui_renderer = UIRenderer(screen, time_manager)

        # Selected entity for inspection
        self.selected_entity = None

    def render(self):
        """Render the entire frame."""
        # Clear screen
        self.screen.fill(config.COLORS["background"])

        # Get camera info
        offset = self.camera.get_offset()
        tile_size = self.camera.get_tile_size()

        # Render world
        self.world_renderer.render(offset, tile_size)

        # Render entities
        self.entity_renderer.render(offset, tile_size, self.selected_entity)

        # Render UI elements (including zoom indicator)
        self.ui_renderer.render(self.selected_entity, self.camera.zoom)

    def handle_camera_input(self, keys: pygame.key.ScancodeWrapper, dt: float):
        """Handle camera movement input."""
        dx = 0
        dy = 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= 1
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += 1
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= 1
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += 1

        if dx != 0 or dy != 0:
            self.camera.move(dx, dy, dt)
            self.camera.clamp_to_world(self.world.width, self.world.height)

    def handle_click(self, screen_x: int, screen_y: int):
        """Handle mouse click."""
        world_x, world_y = self.camera.screen_to_world(screen_x, screen_y)

        # Check if clicked on an entity
        entity = self.entity_manager.get_entity_at_pixel(
            screen_x, screen_y,
            self.camera.get_offset(),
            self.camera.get_tile_size()
        )

        if entity:
            self.selected_entity = entity
        else:
            self.selected_entity = None
