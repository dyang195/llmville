"""World/grid rendering with Wang tile support."""

import pygame

import config
from ..core.world import World, TerrainType
from .asset_manager import get_asset_manager


class WorldRenderer:
    """Renders the world grid and tiles with terrain transitions."""

    def __init__(self, screen: pygame.Surface, world: World):
        self.screen = screen
        self.world = world
        self.asset_manager = get_asset_manager()

        # Terrain colors (fallback if no sprites)
        self.terrain_colors = {
            TerrainType.GRASS: config.COLORS["grass"],
            TerrainType.ROAD: config.COLORS["road"],
            TerrainType.WATER: config.COLORS["water"],
            TerrainType.BUILDING: config.COLORS["building"],
        }

        # Map terrain types to sprite prefixes
        self.terrain_to_prefix = {
            TerrainType.GRASS: "tile_grass",
            TerrainType.ROAD: "tile_road",
            TerrainType.WATER: "tile_water",
        }

        # Cache for scaled tiles
        self.scaled_cache: dict[tuple, pygame.Surface] = {}
        self.last_tile_size = 0

    def render(self, camera_offset: tuple[float, float], tile_size: int):
        """Render visible portion of the world."""
        offset_x, offset_y = camera_offset

        # Clear cache if tile size changed
        if tile_size != self.last_tile_size:
            self.scaled_cache.clear()
            self.last_tile_size = tile_size

        # Calculate visible tile range
        start_x = max(0, int(offset_x // tile_size))
        start_y = max(0, int(offset_y // tile_size))
        end_x = min(self.world.width, int((offset_x + config.WINDOW_WIDTH) // tile_size) + 1)
        end_y = min(self.world.height, int((offset_y + config.WINDOW_HEIGHT) // tile_size) + 1)

        # Render tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                tile = self.world.get_tile(x, y)
                if tile:
                    self._render_tile(x, y, tile, offset_x, offset_y, tile_size)

    def _render_tile(self, x: int, y: int, tile, offset_x: float, offset_y: float, tile_size: int):
        """Render a single tile, using Wang tiles for transitions."""
        screen_x = int(x * tile_size - offset_x)
        screen_y = int(y * tile_size - offset_y)

        terrain = tile.terrain
        sprite = None

        # Use Wang tiles for all terrain rendering
        if terrain == TerrainType.GRASS:
            sprite = self._get_grass_sprite(x, y, tile_size)
        elif terrain == TerrainType.ROAD:
            sprite = self._get_road_sprite(x, y, tile_size)
        elif terrain == TerrainType.WATER:
            sprite = self._get_water_sprite(x, y, tile_size)

        if sprite:
            self.screen.blit(sprite, (screen_x, screen_y))
        else:
            # Fallback to colored rectangle
            color = self.terrain_colors.get(terrain, config.COLORS["grass"])
            pygame.draw.rect(
                self.screen,
                color,
                (screen_x, screen_y, tile_size, tile_size)
            )

    def _get_transition_sprite(self, x: int, y: int, terrain: TerrainType, tile_size: int) -> pygame.Surface:
        """Get Wang tile sprite for terrain transitions."""
        # Check what terrain types are adjacent
        neighbors = self._get_neighbor_terrains(x, y)

        # Check for grass/water transitions
        if TerrainType.WATER in neighbors.values():
            corners = self._calculate_corners(x, y, TerrainType.GRASS, TerrainType.WATER)
            if corners != (1, 1, 1, 1):  # Not all grass
                return self._get_wang_sprite("grass_water", corners, tile_size, x, y)

        # Check for grass/road transitions
        if TerrainType.ROAD in neighbors.values():
            corners = self._calculate_corners(x, y, TerrainType.GRASS, TerrainType.ROAD)
            if corners != (1, 1, 1, 1):  # Not all grass
                return self._get_wang_sprite("grass_dirt", corners, tile_size, x, y)

        return None

    def _get_neighbor_terrains(self, x: int, y: int) -> dict[str, TerrainType]:
        """Get terrain types of all 8 neighbors."""
        neighbors = {}
        for dx, dy, name in [
            (-1, -1, "nw"), (0, -1, "n"), (1, -1, "ne"),
            (-1, 0, "w"), (1, 0, "e"),
            (-1, 1, "sw"), (0, 1, "s"), (1, 1, "se")
        ]:
            tile = self.world.get_tile(x + dx, y + dy)
            if tile:
                neighbors[name] = tile.terrain
        return neighbors

    def _calculate_corners(self, x: int, y: int, upper_terrain: TerrainType, lower_terrain: TerrainType) -> tuple:
        """Calculate corner values for Wang tile lookup.

        Returns (NW, NE, SW, SE) where 1 = upper terrain, 0 = lower terrain.
        A corner is "upper" if the current cell and adjacent cells sharing that corner are upper terrain.
        """

        def get_terrain(dx: int, dy: int) -> TerrainType:
            tile = self.world.get_tile(x + dx, y + dy)
            return tile.terrain if tile else upper_terrain

        current = get_terrain(0, 0)

        # For each corner, check if any adjacent cell that shares it is the lower terrain
        # NW corner: shared with cells at (-1, -1), (-1, 0), (0, -1)
        nw_lower = any(
            get_terrain(dx, dy) == lower_terrain
            for dx, dy in [(-1, 0), (0, -1), (-1, -1)]
        )

        # NE corner: shared with cells at (1, -1), (1, 0), (0, -1)
        ne_lower = any(
            get_terrain(dx, dy) == lower_terrain
            for dx, dy in [(1, 0), (0, -1), (1, -1)]
        )

        # SW corner: shared with cells at (-1, 1), (-1, 0), (0, 1)
        sw_lower = any(
            get_terrain(dx, dy) == lower_terrain
            for dx, dy in [(-1, 0), (0, 1), (-1, 1)]
        )

        # SE corner: shared with cells at (1, 1), (1, 0), (0, 1)
        se_lower = any(
            get_terrain(dx, dy) == lower_terrain
            for dx, dy in [(1, 0), (0, 1), (1, 1)]
        )

        # 1 = upper (grass), 0 = lower (road/water)
        return (
            0 if nw_lower else 1,
            0 if ne_lower else 1,
            0 if sw_lower else 1,
            0 if se_lower else 1
        )

    def _get_wang_sprite(self, tileset_name: str, corners: tuple, tile_size: int, x: int, y: int) -> pygame.Surface:
        """Get and scale a Wang tile sprite."""
        cache_key = (tileset_name, corners, tile_size)
        if cache_key in self.scaled_cache:
            return self.scaled_cache[cache_key]

        nw, ne, sw, se = corners
        sprite = self.asset_manager.get_wang_tile(tileset_name, nw, ne, sw, se)
        if sprite:
            if sprite.get_width() != tile_size:
                sprite = pygame.transform.scale(sprite, (tile_size, tile_size))
            self.scaled_cache[cache_key] = sprite
            return sprite
        return None

    def _get_tile_sprite(self, x: int, y: int, terrain: TerrainType, tile_size: int) -> pygame.Surface:
        """Get a regular tile sprite, scaled appropriately."""
        prefix = self.terrain_to_prefix.get(terrain)
        if not prefix:
            return None

        # Check cache
        cache_key = (prefix, x, y, tile_size)
        if cache_key in self.scaled_cache:
            return self.scaled_cache[cache_key]

        # Get sprite from asset manager
        sprite = self.asset_manager.get_tile_sprite(terrain.value, x, y)
        if sprite:
            scaled = pygame.transform.scale(sprite, (tile_size, tile_size))
            self.scaled_cache[cache_key] = scaled
            return scaled

        return None
