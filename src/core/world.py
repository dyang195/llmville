"""World grid and pathfinding system."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import heapq

import config


class TerrainType(Enum):
    """Types of terrain tiles."""
    GRASS = "grass"
    ROAD = "road"
    WATER = "water"
    BUILDING = "building"


@dataclass
class Tile:
    """A single tile in the world grid."""
    terrain: TerrainType
    walkable: bool = True
    building_id: Optional[str] = None

    def __post_init__(self):
        # Water and buildings are not walkable by default
        if self.terrain == TerrainType.WATER:
            self.walkable = False
        elif self.terrain == TerrainType.BUILDING and self.building_id is None:
            self.walkable = False


@dataclass
class Building:
    """A building in the world."""
    id: str
    name: str
    building_type: str  # shop, home, tavern, etc.
    entrance: tuple[int, int]  # Grid position of entrance


class World:
    """2D grid-based world with pathfinding."""

    def __init__(self, width: int = None, height: int = None):
        self.width = width or config.GRID_WIDTH
        self.height = height or config.GRID_HEIGHT
        self.grid: list[list[Tile]] = []
        self.buildings: dict[str, Building] = {}
        self._initialize_grid()

    def _initialize_grid(self):
        """Create initial grid with default terrain."""
        self.grid = [
            [Tile(terrain=TerrainType.GRASS) for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self._generate_town()

    def _generate_town(self):
        """Generate a simple town layout."""
        # Create main road (horizontal through middle)
        road_y = self.height // 2
        for x in range(self.width):
            self.grid[road_y][x] = Tile(terrain=TerrainType.ROAD)

        # Create vertical road
        road_x = self.width // 2
        for y in range(self.height):
            self.grid[y][road_x] = Tile(terrain=TerrainType.ROAD)

        # Add some buildings along the roads
        building_positions = [
            (road_x - 3, road_y - 3, "shop", "General Store"),
            (road_x + 3, road_y - 3, "tavern", "The Rusty Tankard"),
            (road_x - 3, road_y + 3, "blacksmith", "Ironworks"),
            (road_x + 3, road_y + 3, "home", "Town Hall"),
        ]

        for bx, by, btype, name in building_positions:
            if 0 <= bx < self.width and 0 <= by < self.height:
                building_id = f"{btype}_{bx}_{by}"
                self.buildings[building_id] = Building(
                    id=building_id,
                    name=name,
                    building_type=btype,
                    entrance=(bx, by + 1)
                )
                # Mark building tiles (2x2)
                for dx in range(2):
                    for dy in range(2):
                        tx, ty = bx + dx, by + dy
                        if 0 <= tx < self.width and 0 <= ty < self.height:
                            self.grid[ty][tx] = Tile(
                                terrain=TerrainType.BUILDING,
                                walkable=False,
                                building_id=building_id
                            )

        # Add a small pond
        pond_x, pond_y = 10, 10
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                tx, ty = pond_x + dx, pond_y + dy
                if 0 <= tx < self.width and 0 <= ty < self.height:
                    if abs(dx) + abs(dy) <= 3:  # Rough circle
                        self.grid[ty][tx] = Tile(terrain=TerrainType.WATER)

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        """Get tile at position, or None if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return None

    def is_walkable(self, x: int, y: int) -> bool:
        """Check if position is walkable."""
        tile = self.get_tile(x, y)
        return tile is not None and tile.walkable

    def get_neighbors(self, x: int, y: int, diagonal: bool = False) -> list[tuple[int, int]]:
        """Get walkable neighboring positions."""
        neighbors = []
        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]  # Up, Down, Left, Right

        if diagonal:
            directions += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                neighbors.append((nx, ny))

        return neighbors

    def find_path(self, start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
        """A* pathfinding from start to end. Returns list of positions or empty list if no path."""
        if not self.is_walkable(end[0], end[1]):
            return []

        if start == end:
            return [start]

        def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        open_set = [(0, start)]
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score: dict[tuple[int, int], float] = {start: 0}
        f_score: dict[tuple[int, int], float] = {start: heuristic(start, end)}
        open_set_hash = {start}

        while open_set:
            _, current = heapq.heappop(open_set)
            open_set_hash.discard(current)

            if current == end:
                # Reconstruct path
                path = [current]
                while current in came_from:
                    current = came_from[current]
                    path.append(current)
                path.reverse()
                return path

            for neighbor in self.get_neighbors(current[0], current[1]):
                tentative_g = g_score[current] + 1

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, end)

                    if neighbor not in open_set_hash:
                        heapq.heappush(open_set, (f_score[neighbor], neighbor))
                        open_set_hash.add(neighbor)

        return []  # No path found

    def get_random_walkable_position(self) -> tuple[int, int]:
        """Get a random walkable position in the world."""
        import random
        walkable = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if self.is_walkable(x, y)
        ]
        return random.choice(walkable) if walkable else (0, 0)
