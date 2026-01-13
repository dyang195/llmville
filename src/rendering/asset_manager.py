"""Asset loading and management for sprites with directional and animation support."""

import os
import json
import random
import pygame
from typing import Optional


# 4 cardinal directions
DIRECTIONS = ["south", "west", "east", "north"]

# Map 8 directions to 4 cardinal
DIRECTION_MAP = {
    "south": "south",
    "north": "north",
    "east": "east",
    "west": "west",
    "south-east": "east",
    "south-west": "west",
    "north-east": "east",
    "north-west": "west",
    "se": "east",
    "sw": "west",
    "ne": "east",
    "nw": "west",
    "s": "south",
    "n": "north",
    "e": "east",
    "w": "west",
    "down": "south",
    "up": "north",
    "left": "west",
    "right": "east"
}


class Animation:
    """Holds frames for an animation."""

    def __init__(self, name: str):
        self.name = name
        self.frames: list[pygame.Surface] = []
        self.frame_duration = 0.1  # seconds per frame

    def add_frame(self, frame: pygame.Surface):
        self.frames.append(frame)

    def get_frame(self, time: float) -> pygame.Surface:
        """Get frame based on elapsed time."""
        if not self.frames:
            return None
        frame_idx = int(time / self.frame_duration) % len(self.frames)
        return self.frames[frame_idx]


class CharacterSprites:
    """Holds all directional sprites and animations for a character."""

    def __init__(self, name: str):
        self.name = name
        self.directions: dict[str, pygame.Surface] = {}  # Static sprites
        self.animations: dict[str, dict[str, Animation]] = {}  # anim_name -> direction -> Animation

    def add_direction(self, direction: str, sprite: pygame.Surface):
        self.directions[direction] = sprite

    def add_animation_frame(self, anim_name: str, direction: str, frame: pygame.Surface):
        if anim_name not in self.animations:
            self.animations[anim_name] = {}
        if direction not in self.animations[anim_name]:
            self.animations[anim_name][direction] = Animation(anim_name)
        self.animations[anim_name][direction].add_frame(frame)

    def get_sprite(self, direction: str, is_moving: bool = False, anim_time: float = 0) -> Optional[pygame.Surface]:
        """Get appropriate sprite - animated if moving, static otherwise."""
        # Normalize direction to cardinal
        direction = DIRECTION_MAP.get(direction.lower(), "south")

        # If moving and walk animation exists, use it
        if is_moving and "walk" in self.animations:
            if direction in self.animations["walk"]:
                anim = self.animations["walk"][direction]
                frame = anim.get_frame(anim_time)
                if frame:
                    return frame

        # Fall back to static sprite
        return self.directions.get(direction) or self.get_default()

    def get_default(self) -> Optional[pygame.Surface]:
        """Get south-facing sprite as default."""
        return self.directions.get("south") or next(iter(self.directions.values()), None)

    def has_animations(self) -> bool:
        return len(self.animations) > 0


class WangTileset:
    """Holds Wang tileset data for terrain transitions."""

    def __init__(self, name: str, tileset_image: pygame.Surface, metadata: dict):
        self.name = name
        self.tileset_image = tileset_image
        self.tiles: dict[tuple, pygame.Surface] = {}  # (NW, NE, SW, SE) -> tile surface
        self.lower_terrain = metadata.get("lower_description", "lower")
        self.upper_terrain = metadata.get("upper_description", "upper")

        # Parse tiles from metadata
        tile_data = metadata.get("tileset_data", {}).get("tiles", [])
        for tile in tile_data:
            corners = tile.get("corners", {})
            bbox = tile.get("bounding_box", {})

            # Create corner key (NW, NE, SW, SE) as tuple of 0/1
            # 0 = lower terrain, 1 = upper terrain
            nw = 1 if corners.get("NW") == "upper" else 0
            ne = 1 if corners.get("NE") == "upper" else 0
            sw = 1 if corners.get("SW") == "upper" else 0
            se = 1 if corners.get("SE") == "upper" else 0
            corner_key = (nw, ne, sw, se)

            # Extract tile from tileset image
            x, y = bbox.get("x", 0), bbox.get("y", 0)
            w, h = bbox.get("width", 32), bbox.get("height", 32)
            try:
                tile_surface = tileset_image.subsurface((x, y, w, h)).copy()
                self.tiles[corner_key] = tile_surface
            except ValueError as e:
                print(f"Failed to extract tile at ({x}, {y}): {e}")

    def get_tile(self, nw: int, ne: int, sw: int, se: int) -> Optional[pygame.Surface]:
        """Get tile for given corner configuration (0=lower, 1=upper)."""
        return self.tiles.get((nw, ne, sw, se))


class AssetManager:
    """Loads and manages game sprites with directional and animation support."""

    def __init__(self):
        self.sprites: dict[str, pygame.Surface] = {}
        self.sprite_variants: dict[str, list[pygame.Surface]] = {}
        self.character_sets: dict[str, list[CharacterSprites]] = {"male": [], "female": []}
        self.entity_characters: dict[str, CharacterSprites] = {}
        self.wang_tilesets: dict[str, WangTileset] = {}  # name -> WangTileset
        self.scaled_cache: dict[tuple, pygame.Surface] = {}
        self.base_path = self._find_assets_path()
        self.loaded = False

    def _find_assets_path(self) -> str:
        if os.path.exists("assets"):
            return "assets"
        file_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(file_dir))
        assets_path = os.path.join(project_root, "assets")
        if os.path.exists(assets_path):
            return assets_path
        return "assets"

    def load_all(self):
        if self.loaded:
            return

        self._load_character_sprites("male")
        self._load_character_sprites("female")
        self._load_tile_variants("tiles/grass", "tile_grass")
        self._load_tile_variants("tiles/road", "tile_road")
        self._load_tile_variants("tiles/water", "tile_water")
        self._load_simple_variants("buildings", "building")

        # Load Wang tilesets for terrain transitions
        self._load_wang_tileset("tiles/grass_dirt", "grass_dirt")
        self._load_wang_tileset("tiles/grass_water", "grass_water")

        self.loaded = True
        male_count = len(self.character_sets["male"])
        female_count = len(self.character_sets["female"])
        print(f"Assets loaded: {male_count} male characters, {female_count} female characters")

    def _load_character_sprites(self, gender: str):
        char_path = os.path.join(self.base_path, "characters", gender)
        if not os.path.exists(char_path):
            return

        for char_name in os.listdir(char_path):
            char_dir = os.path.join(char_path, char_name)
            if not os.path.isdir(char_dir):
                continue

            character = CharacterSprites(char_name)

            # Load static rotations
            rotations_dir = os.path.join(char_dir, "rotations")
            if os.path.exists(rotations_dir):
                for direction in DIRECTIONS:
                    sprite_path = os.path.join(rotations_dir, f"{direction}.png")
                    if os.path.exists(sprite_path):
                        try:
                            sprite = pygame.image.load(sprite_path).convert_alpha()
                            character.add_direction(direction, sprite)
                        except pygame.error as e:
                            print(f"Failed to load {sprite_path}: {e}")

            # Load animations
            animations_dir = os.path.join(char_dir, "animations")
            if os.path.exists(animations_dir):
                for anim_name in os.listdir(animations_dir):
                    anim_path = os.path.join(animations_dir, anim_name)
                    if not os.path.isdir(anim_path):
                        continue

                    # Map animation folder names (e.g., "walking-8-frames" -> "walk")
                    simple_name = "walk" if "walk" in anim_name.lower() else anim_name

                    for direction in os.listdir(anim_path):
                        dir_path = os.path.join(anim_path, direction)
                        if not os.path.isdir(dir_path):
                            continue

                        # Load frames in order
                        frames = sorted([f for f in os.listdir(dir_path) if f.endswith('.png')])
                        for frame_file in frames:
                            frame_path = os.path.join(dir_path, frame_file)
                            try:
                                frame = pygame.image.load(frame_path).convert_alpha()
                                character.add_animation_frame(simple_name, direction, frame)
                            except pygame.error as e:
                                print(f"Failed to load {frame_path}: {e}")

            if character.directions:
                self.character_sets[gender].append(character)
                anim_info = f" + {len(character.animations)} animations" if character.has_animations() else ""
                print(f"  Loaded {char_name}: {len(character.directions)} directions{anim_info}")

    def _load_tile_variants(self, subdir: str, prefix: str):
        full_path = os.path.join(self.base_path, subdir)
        if not os.path.exists(full_path):
            return

        variants = []

        # Load tileset.png if exists
        tileset_path = os.path.join(full_path, "tileset.png")
        if os.path.exists(tileset_path):
            try:
                tileset = pygame.image.load(tileset_path).convert_alpha()
                tile_size = 32
                for row in range(4):
                    for col in range(4):
                        tile = tileset.subsurface((col * tile_size, row * tile_size, tile_size, tile_size))
                        variants.append(tile.copy())
            except pygame.error as e:
                print(f"Failed to load tileset {tileset_path}: {e}")

        # Load individual PNGs
        for filename in sorted(os.listdir(full_path)):
            if filename.lower().endswith('.png') and filename != 'tileset.png':
                sprite_path = os.path.join(full_path, filename)
                try:
                    sprite = pygame.image.load(sprite_path).convert_alpha()
                    variants.append(sprite)
                except pygame.error as e:
                    print(f"Failed to load {sprite_path}: {e}")

        if variants:
            self.sprite_variants[prefix] = variants
            print(f"  Loaded {prefix}: {len(variants)} tiles")

    def _load_simple_variants(self, subdir: str, prefix: str):
        full_path = os.path.join(self.base_path, subdir)
        if not os.path.exists(full_path):
            return

        variants = []
        for filename in sorted(os.listdir(full_path)):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                sprite_path = os.path.join(full_path, filename)
                try:
                    sprite = pygame.image.load(sprite_path).convert_alpha()
                    variants.append(sprite)
                    self.sprites[f"{prefix}_{os.path.splitext(filename)[0]}"] = sprite
                except pygame.error as e:
                    print(f"Failed to load {sprite_path}: {e}")

        if variants:
            self.sprite_variants[prefix] = variants

    def _load_wang_tileset(self, subdir: str, name: str):
        """Load a Wang tileset from tileset.png and metadata.json."""
        full_path = os.path.join(self.base_path, subdir)
        tileset_path = os.path.join(full_path, "tileset.png")
        metadata_path = os.path.join(full_path, "metadata.json")

        if not os.path.exists(tileset_path) or not os.path.exists(metadata_path):
            return

        try:
            tileset_image = pygame.image.load(tileset_path).convert_alpha()
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            wang_tileset = WangTileset(name, tileset_image, metadata)
            self.wang_tilesets[name] = wang_tileset
            print(f"  Loaded Wang tileset {name}: {len(wang_tileset.tiles)} tiles")
        except (pygame.error, json.JSONDecodeError, IOError) as e:
            print(f"Failed to load Wang tileset {name}: {e}")

    def get_wang_tile(self, tileset_name: str, nw: int, ne: int, sw: int, se: int) -> Optional[pygame.Surface]:
        """Get a Wang tile for given corner configuration."""
        tileset = self.wang_tilesets.get(tileset_name)
        if tileset:
            return tileset.get_tile(nw, ne, sw, se)
        return None

    def has_wang_tileset(self, name: str) -> bool:
        """Check if a Wang tileset is loaded."""
        return name in self.wang_tilesets

    def assign_entity_character(self, entity_id: str, gender: str = "male") -> Optional[CharacterSprites]:
        if entity_id in self.entity_characters:
            return self.entity_characters[entity_id]

        char_list = self.character_sets.get(gender, [])
        if not char_list:
            char_list = self.character_sets.get("male", []) or self.character_sets.get("female", [])

        if char_list:
            character = random.choice(char_list)
            self.entity_characters[entity_id] = character
            return character
        return None

    def get_entity_sprite(self, entity_id: str, direction: str, tile_size: int,
                          is_moving: bool = False, anim_time: float = 0) -> Optional[pygame.Surface]:
        """Get sprite for entity, with animation support."""
        character = self.entity_characters.get(entity_id)
        if not character:
            return None

        sprite = character.get_sprite(direction, is_moving, anim_time)
        if sprite:
            return self._scale_sprite(sprite, tile_size, entity_id, direction, is_moving, anim_time)
        return None

    def _scale_sprite(self, sprite: pygame.Surface, tile_size: int, entity_id: str,
                      direction: str, is_moving: bool, anim_time: float) -> pygame.Surface:
        # For animations, include frame index in cache key
        if is_moving:
            frame_idx = int(anim_time / 0.1) % 8
            cache_key = (entity_id, direction, tile_size, "walk", frame_idx)
        else:
            cache_key = (entity_id, direction, tile_size, "static", 0)

        if cache_key in self.scaled_cache:
            return self.scaled_cache[cache_key]

        if sprite.get_width() != tile_size:
            scaled = pygame.transform.scale(sprite, (tile_size, tile_size))
        else:
            scaled = sprite

        self.scaled_cache[cache_key] = scaled
        return scaled

    def get_tile_sprite(self, tile_type: str, x: int, y: int) -> Optional[pygame.Surface]:
        prefix = f"tile_{tile_type}"
        variants = self.sprite_variants.get(prefix, [])
        if not variants:
            return None
        index = (x * 7 + y * 13) % len(variants)
        return variants[index]

    def has_sprites(self, prefix: str) -> bool:
        return prefix in self.sprite_variants and len(self.sprite_variants[prefix]) > 0

    def has_characters(self, gender: str = None) -> bool:
        if gender:
            return len(self.character_sets.get(gender, [])) > 0
        return any(len(chars) > 0 for chars in self.character_sets.values())

    def clear_scaled_cache(self):
        self.scaled_cache.clear()


_asset_manager: Optional[AssetManager] = None

def get_asset_manager() -> AssetManager:
    global _asset_manager
    if _asset_manager is None:
        _asset_manager = AssetManager()
    return _asset_manager
