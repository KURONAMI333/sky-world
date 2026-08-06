# Changelog

All notable changes to Sky World follow this file. Format roughly follows
[Keep a Changelog](https://keepachangelog.com/); versions before 1.0.0 were
development-only and not released.

## [2.0.0] — unreleased

Requires Isekai API 2.1.0. **World-generation change: existing worlds keep their
old terrain — start a new world.**

### Added
- Three altitude tiers instead of one uniform band. Low tier Y=8..100 (broad,
  sparse), main tier Y=90..202 (dense, where you live), high tier Y=198..256
  (small, rare), combined with `minecraft:max`.
- Island undersides taper. Each tier's noise is multiplied by a
  `minecraft:y_clamped_gradient` over the lower part of its band, so density
  falls off quadratically downward instead of mirroring the top.
- Dimension-wide visibility range — `client_atmosphere.fog_near_distance` 64,
  `fog_far_distance` 256, so distant islands read as haze.

### Changed
- `applies_to` is the `#minecraft:is_overworld` tag instead of 36 hand-written
  biome ids. The 17 biomes the list had missed (9 oceans, 3 badlands, river and
  frozen_river, lush_caves, dripstone_caves, deep_dark) now get the worldshape,
  so ore remap and structure predicates no longer have holes.
- `ore_strategy` is `isekai_api:column_local` (`scale: proportional`) instead of
  `linear`. Ore depth resolves against each column's own surface and underside,
  which is what a world of islands at different altitudes needs.
- `playable_range` Y=8..256 and `default_structure_predicate`'s `y_in_range`
  28..246, to bracket the new tiers.

### Removed
- The `sky_world:skyrealm` dimension, its `dimension_type`, its `noise_settings`
  and the `ethereal_grove` biome. It had no portal and no way in short of
  `/execute in`, and its terrain was a copy of the overworld's.
- `atmosphere.sky_color` / `fog_color`. The sky is vanilla's per-biome colour
  again; the green sky is gone.
- `content_overrides.block_overrides` (cherry_grove quartz/calcite).

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
