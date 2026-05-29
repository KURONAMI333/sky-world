# Sky World — Runtime Test Checklist

Run this after `./gradlew runClient` from `mod-030-sky-world/`. Both Isekai API
and Sky World should load — verify via the mod list at the title screen.

## 1. Mod load (title screen)

- [ ] Mods button → `Isekai API 1.0.0` listed
- [ ] Mods button → `Sky World 1.0.0` listed
- [ ] No red-banner load errors

Log evidence (in `run/logs/latest.log`):
```
[Isekai] loading v1.0.0
Sky World v1.0.0 loading
[Isekai] commands registered: /isekai version|reload|stats|...
```

## 2. Create new world

- [ ] Singleplayer → Create New World
- [ ] World Type: **Default** (not Superflat)
- [ ] **Allow Cheats: ON** (needed for /isekai commands)
- [ ] Game Mode: Creative (faster to test)
- [ ] Generate World

## 3. Visual confirmation — floating islands

- [ ] You spawn on solid ground around Y=180
- [ ] `/tp @s ~ 100 ~` — Y=100 should be **void** (no ground)
- [ ] `/tp @s ~ 220 ~` — Y=220 should be **sky** (above island)
- [ ] Fly out horizontally (~500 blocks) — terrain continues as island chunks
- [ ] Look down from Y=250 — see islands separated by void

## 4. Isekai snapshot

```
/isekai stats
```
Expected:
- PlacedFeatures: ~233 (vanilla overworld feature count)
- Structure placements: ~34
- Mob spawn entries: ~700+
- **Declared worldshape dimensions: 1** (sky_world's worldshape registered)

```
/isekai query dimensions
```
Expected: lists `minecraft:overworld`

```
/isekai query worldshape minecraft:overworld
```
Expected: shows the active descriptor (playable_range 120..220, etc.)

## 5. Structure exclusion

```
/locate structure minecraft:ocean_monument
```
Expected: **"Could not find a structure of type minecraft:ocean_monument nearby"**
(structure_modifier cleared its biome filter)

```
/locate structure minecraft:ancient_city
```
Expected: same not-found result.

```
/locate structure minecraft:village_plains
```
Expected: returns coordinates (villages SHOULD spawn on islands per default_structure_predicate).

## 6. Ore placement

Mine through an island — expect to find:
- [ ] Coal / iron / copper near Y=140-180 (linearly remapped from vanilla 0..256)
- [ ] Diamond ore deep in island Y=120-140 (remapped from vanilla -64..16)
- [ ] No deepslate-only ores blocked by missing deepslate (vanilla strata don't apply since terrain is just stone in the band)

## 7. Carver exclusion

- [ ] Tunnel through an island top-to-bottom — should be solid stone with no cave systems
- [ ] No ravines either (canyon carver excluded)

## 8. Dump for inspection

```
/isekai dump worldgen
```
- [ ] File `<world>/isekai_dump/worldgen.txt` is produced
- [ ] Contains ~233 placed features + ~34 structure placements

## Known things to watch for

- **Spawn position bug**: vanilla picks spawn Y by Heightmap, which might
  miscalculate inside floating islands. If you spawn in a wall, fly out.
- **Bedrock**: no bedrock at Y=-64 since terrain doesn't reach down there.
  The void is the floor.
- **Sky color**: should look slightly different from vanilla (atmosphere
  override applied — sky color #8FCFC7 = pale cyan, fog #CCB0D9 = lavender).

## If something fails

- Reload failed → check `run/logs/latest.log` for stack trace, share with claude
- Terrain looks like vanilla → `noise_settings/overworld.json` overlay didn't apply (verify the file exists in `build/resources/main/data/minecraft/worldgen/noise_settings/overworld.json`)
- `/isekai stats` shows `Declared worldshape dimensions: 0` → the biome_modifier's worldshape didn't reach IsekaiRemap singleton; this is by design (biome modifiers go through NeoForge registry, not the Java API). Still functions for chunk-gen.
