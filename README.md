# Sky World

> The overworld becomes three bands of floating islands with open void between them.
> Vanilla ores, structures, and mobs are remapped into the island rock via [Isekai API](https://github.com/KURONAMI333/isekai-api).

[![License: All Rights Reserved](https://img.shields.io/badge/License-All%20Rights%20Reserved-lightgrey.svg)](LICENSE)
[![NeoForge 1.21.1](https://img.shields.io/badge/NeoForge-1.21.1-orange.svg)](https://neoforged.net)
[![Depends on Isekai API](https://img.shields.io/badge/Depends-Isekai%20API%202.1.0-9333ea)](https://github.com/KURONAMI333/isekai-api)

---

## Concept

The overworld is rewritten as islands at three altitudes with empty air between them, so the layers read as separate levels rather than one thick slab.

| Band | Y | Character |
|---|---|---|
| Lower | 30–78 | Large islands, widely spaced. Long crossings. |
| Middle | 116–176 | Where you live. Denser, most of the land. |
| Upper | 212–242 | Small and rare. Stepping stones near the clouds. |

Villages, ravines, strongholds, and ore veins all relocate into the island volume — you mine *through* an island instead of *down* to bedrock.

Pairs naturally with bridge mods (YUNG's Bridges), airship mods (Create: Aeronautics), and view-distance mods (Distant Horizons).

## How it works

Almost all of it is datapack JSON. The one piece of Java raises the cloud plane above the top band, because cloud height is not reachable from a datapack.

1. **`data/minecraft/worldgen/noise_settings/overworld.json`** — replaces the overworld's noise settings. Terrain is three `isekai_api:band_density` layers joined with `minecraft:max`; the surface layer is the one-line `isekai_api:vanilla_overworld_surface` delegate, so the grass/sand/badlands/snow rules stay exactly vanilla without copying the 30 KB rule tree.
2. **`data/sky_world/isekai/worldshape/sky.json`** — the worldshape. It applies to `#minecraft:is_overworld`, remaps ores with `isekai_api:column_local` so they follow each island's own top and bottom rather than absolute depth, excludes carvers and the vanilla springs and lava lakes that would pour off an island rim, and sets the fog distances.
3. **`data/sky_world/worldgen/{configured,placed}_feature/pond_water.json`** — the water. There is no ocean, so ponds carved into the islands are the whole supply.
4. **`SkyWorldDimensionEffects`** — the cloud plane, moved from Y 192 to Y 264.

Same Isekai primitives any third-party modder gets — Sky World is just one application.

## How to play

1. Install [Isekai API](https://github.com/KURONAMI333/isekai-api) and Sky World together.
2. Create a new world. **Updating an existing 1.0.0 world does not work** — the island layout changed, so newly explored chunks will not line up with what you have already generated.
3. You spawn on a middle-band island. Falling off the edge is the main way to die.
4. Mine through the island for ores. Bridge or fly to nearby islands.

## Dependencies

- NeoForge 1.21.1
- [Isekai API 2.1.0+](https://github.com/KURONAMI333/isekai-api) (required)

## Building from source

```bash
./gradlew build
```

Produces `build/libs/sky_world-2.0.0.jar`.

## Compatibility

Because Sky World overlays `data/minecraft/worldgen/noise_settings/overworld.json`, it conflicts with any other mod that does the same (Terralith, BYG, and the other Isekai world mods). It coexists with:

- Bridge mods (YUNG's Bridges)
- Airship / flight mods (Create: Aeronautics, Iron Jetpacks)
- View-distance mods (Distant Horizons)
- Most QoL mods (JEI, Sodium, Iris, etc.)

## License

[All Rights Reserved](LICENSE) — modpack inclusion welcome, no credit required. Source is published so you can read exactly what it does.

## Credits

- Author: KURONAMI
- Built on [Isekai API](https://github.com/KURONAMI333/isekai-api)
