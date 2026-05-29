# Sky World

> The overworld becomes a sea of Aether II-style continental floating islands.
> Below the islands is the void. Vanilla ores, structures, and mobs are remapped onto the islands via [Isekai API](https://github.com/KURONAMI333/isekai-api).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![NeoForge 1.21.1](https://img.shields.io/badge/NeoForge-1.21.1-orange.svg)](https://neoforged.net)
[![Depends on Isekai API](https://img.shields.io/badge/Depends-Isekai%20API-9333ea)](https://github.com/KURONAMI333/isekai-api)

---

## Concept

Every chunk of the overworld is rewritten as thick floating islands separated by open void. Villages, ravines, strongholds, and ore veins all relocate into the island volume — you mine *through* the island instead of *down* to bedrock.

Pairs naturally with bridge mods (YUNG's Bridges), airship mods (Create: Aeronautics), and view-distance mods (Distant Horizons).

## How it works

Sky World ships **only datapack JSON** — no custom blocks, no custom mobs, no Mixins of its own. The whole world transformation is expressed in three files:

1. **`data/minecraft/worldgen/noise_settings/overworld.json`** — overlay that wraps vanilla's `final_density` in Isekai's `mask_y_range`, forcing solid terrain into the Y=120..220 band and leaving void elsewhere.
2. **`data/sky_world/neoforge/biome_modifier/apply_sky.json`** — a NeoForge biome modifier of type `isekai_api:apply_worldshape` that:
   - Remaps every ore feature's Y range into the island band (via Isekai's `Linear` `RemapStrategy`)
   - Excludes all overworld carvers — no caves inside the islands
   - Filters which biomes the modification applies to (most surface land biomes)
3. **`data/sky_world/neoforge/structure_modifier/apply_sky.json`** — a structure modifier that strips ocean / ancient-city structures (which can't fit the sky-only worldshape) by clearing their biome filter.

That's the whole mod. Same Isekai primitives any third-party modder gets — Sky World is just one application.

## How to play

1. Install [Isekai API](https://github.com/KURONAMI333/isekai-api) and Sky World together.
2. Create a new world (existing worlds keep their old terrain in already-generated chunks).
3. You spawn at the surface (~Y=180 on a floating island). Below ~Y=120 is void; falling off the edge of your island = death.
4. Mine through the island for ores. Bridge or fly to nearby islands.

## Dependencies

- NeoForge 1.21.1
- [Isekai API 1.0.0+](https://github.com/KURONAMI333/isekai-api) (required, loaded automatically)

## Building from source

```bash
./gradlew build
```

Produces `build/libs/sky_world-1.0.0.jar`.

## Compatibility

Because Sky World **overlays** `data/minecraft/worldgen/noise_settings/overworld.json`, it conflicts with any other mod that does the same (Terralith, BYG, etc.). It coexists with:

- Bridge mods (YUNG's Bridges)
- Airship / flight mods (Create: Aeronautics, Iron Jetpacks)
- View-distance mods (Distant Horizons)
- Most QoL mods (JEI, Sodium, Iris, etc.)

## License

[MIT License](LICENSE) — modpack inclusion welcome, no credit required.

## Credits

- Author: KURONAMI
- Built on [Isekai API](https://github.com/KURONAMI333/isekai-api)
