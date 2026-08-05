# Changelog

All notable changes to Sky World follow this file. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/); versions before 1.0.0 were
development-only and not released.

## [1.1.0] — 2026-08-05

Requires Isekai API 2.x. No world-generation change: terrain, biomes, ores,
structures and surface blocks are identical to 1.0.0.

### Changed
- Both `noise_settings` documents (`minecraft:overworld` and `sky_world:skyrealm`)
  state the surface as Isekai's `isekai_api:vanilla_overworld_surface` delegate
  instead of an expanded copy of the vanilla surface-rule tree — 2427 → 197 and
  2419 → 184 lines. The delegate reconstructs the same vanilla overworld surface
  at runtime, so the emitted blocks are unchanged.
- Router axes that the engine never samples with `aquifers_enabled: false` and
  `ore_veins_enabled: false` (`barrier`, `fluid_level_floodedness`,
  `fluid_level_spread`, `lava`, `vein_toggle`, `vein_ridged`, `vein_gap`) are
  stated as `minecraft:zero`. Every axis that *is* sampled — `continents`,
  `erosion`, `depth`, `ridges`, `temperature`, `vegetation`,
  `initial_density_without_jaggedness` — stays byte-identical to vanilla, and
  `final_density` keeps the Y=50..200 `band_density` island shape.
- Worldshape and biome-source `"type"` ids use the canonical `isekai_api:`
  prefix (the bare `isekai:` prefix is deprecated in Isekai API 2.x).
- The build resolves Isekai API from its raw-URL maven repo, so this repo builds
  without a sibling checkout.

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
