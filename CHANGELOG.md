# Changelog

All notable changes to Sky World follow this file. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/); versions before 1.0.0 were
development-only and not released.

## [1.0.0] — 2026-05-28

First public release. Datapack-only Aether-style floating-island overworld
built on Isekai API.

### World transformation
- `data/minecraft/worldgen/noise_settings/overworld.json` — overlay wrapping
  vanilla `final_density` in Isekai's `mask_y_range` (Y=120..220 inside =
  vanilla terrain, outside = `constant -1.0` = void).
- `data/sky_world/neoforge/biome_modifier/apply_sky.json` — Isekai
  `apply_worldshape` biome modifier:
  - `playable_range` Y=120..220
  - `ore_strategy: linear` — every ore's Y band linearly remaps into the
    island volume
  - `default_structure_predicate` requires `y_in_range(120, 220)` AND
    `solid_floor(clearance=2)` so structures only spawn on viable platforms
  - per-structure `never` predicates for `ocean_monument`, all `shipwreck`
    variants, `ocean_ruin_*`, `buried_treasure`, `ancient_city`
  - 35 surface land biomes in `applies_to` (oceans / caves / void excluded)
  - all four overworld carvers excluded (no caves inside islands)
  - atmosphere tint: sky color #8FCFC7, fog color #CCB0D9
- `data/sky_world/neoforge/structure_modifier/apply_sky.json` — Isekai
  `apply_worldshape_structures` modifier clears biome filters for the
  ocean / ancient-city structures so they never attempt placement.

### Java surface
- Single `SkyWorld.java` `@Mod` entry. Smoke-tests the Isekai facade is
  reachable; no other Java code.

### Known limitations
- New worlds only — already-generated chunks keep their vanilla terrain.
- Conflicts with any mod that also overlays
  `data/minecraft/worldgen/noise_settings/overworld.json` (Terralith, BYG,
  etc.). Run one or the other.
- Spawn position is computed by vanilla and may land inside an island block;
  the player typically respawns or you teleport out.
- Strongholds may still attempt placement near void edges; the spatial
  predicate gates them but doesn't always succeed at finding a valid spot.
