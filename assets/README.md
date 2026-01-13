# Asset Directory Structure

Place your sprites in the following directories. The game will automatically load and use them.

## Directory Layout

```
assets/
├── characters/
│   ├── male/           # Male character sprites (randomly assigned)
│   │   ├── villager1.png
│   │   ├── villager2.png
│   │   └── merchant.png
│   └── female/         # Female character sprites (randomly assigned)
│       ├── villager1.png
│       └── farmer.png
├── tiles/
│   ├── grass/          # Grass tile variants (auto-varied by position)
│   │   ├── grass1.png
│   │   ├── grass2.png
│   │   └── grass3.png
│   ├── road/           # Road tiles
│   └── water/          # Water tiles
└── buildings/          # Building sprites (larger than tiles)
    ├── shop.png
    └── house.png
```

## Sprite Dimensions

| Asset Type | Size | Notes |
|------------|------|-------|
| Characters | **32x32 px** | Square, transparent background |
| Grass/Road/Water tiles | **32x32 px** | Tileable, no transparency needed |
| Buildings | **64x64 px** or **96x96 px** | Transparent background |

## File Format
- PNG with transparency (recommended)
- JPG, BMP also supported

---

# PixelLab Prompts

Copy these prompts into PixelLab to generate matching sprites.

## Male Characters (32x32)

```
pixel art, 32x32 sprite, male villager character, medieval fantasy RPG style, front-facing idle pose, simple design, warm earthy colors, transparent background
```

```
pixel art, 32x32 sprite, male merchant character, medieval fantasy, brown tunic, front-facing, simple clean lines, transparent background
```

```
pixel art, 32x32 sprite, male farmer character, medieval fantasy, straw hat, pitchfork optional, front-facing idle, transparent background
```

```
pixel art, 32x32 sprite, male blacksmith character, medieval fantasy, leather apron, muscular, front-facing, transparent background
```

```
pixel art, 32x32 sprite, male guard character, medieval fantasy, simple armor, helmet, front-facing idle pose, transparent background
```

## Female Characters (32x32)

```
pixel art, 32x32 sprite, female villager character, medieval fantasy RPG style, front-facing idle pose, dress, simple design, transparent background
```

```
pixel art, 32x32 sprite, female shopkeeper character, medieval fantasy, apron, friendly appearance, front-facing, transparent background
```

```
pixel art, 32x32 sprite, female farmer character, medieval fantasy, simple dress, headscarf optional, front-facing idle, transparent background
```

```
pixel art, 32x32 sprite, female innkeeper character, medieval fantasy, serving tray optional, warm colors, front-facing, transparent background
```

## Grass Tiles (32x32)

```
pixel art, 32x32 tile, grass terrain, top-down view, lush green, slight variation, tileable seamless, RPG game style
```

```
pixel art, 32x32 tile, grass with small flowers, top-down view, green with tiny yellow/white flowers, tileable, RPG style
```

```
pixel art, 32x32 tile, grass with dirt patches, top-down view, green grass with brown dirt spots, tileable seamless
```

## Road Tiles (32x32)

```
pixel art, 32x32 tile, dirt road path, top-down view, brown/tan earth, worn footpath, tileable seamless, RPG game style
```

```
pixel art, 32x32 tile, cobblestone road, top-down view, gray stones, medieval style, tileable seamless
```

## Water Tiles (32x32)

```
pixel art, 32x32 tile, water pond, top-down view, blue water, slight ripples, tileable seamless, RPG style
```

## Buildings (64x64)

```
pixel art, 64x64 sprite, medieval cottage house, front view, thatched roof, wooden walls, RPG game style, transparent background
```

```
pixel art, 64x64 sprite, medieval shop building, front view, hanging sign, wooden structure, fantasy RPG style, transparent background
```

```
pixel art, 64x64 sprite, medieval tavern inn, front view, two stories, warm lighting in windows, RPG style, transparent background
```

```
pixel art, 64x64 sprite, medieval blacksmith forge, front view, smoke from chimney, anvil visible, RPG style, transparent background
```

---

## Tips for Best Results

1. **Consistency**: Generate all characters in one session to maintain style
2. **Transparency**: If PixelLab doesn't give transparent backgrounds, use remove.bg or manually edit
3. **Variations**: For grass, generate 2-3 variants to avoid repetitive patterns
4. **Naming**: Name files descriptively (e.g., `villager_male_1.png`, `grass_flowers.png`)

## Alternative: Quick Color Palette

If you want cohesive colors, use this palette:
- Grass: `#4C994C`, `#3D7A3D`, `#5CAD5C`
- Road: `#8B7765`, `#A08060`
- Skin tones: `#E8C4A8`, `#D4A574`, `#8B6914`
- Clothing: `#4A6FA5`, `#8B4513`, `#556B2F`, `#800020`
