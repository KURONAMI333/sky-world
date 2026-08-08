#!/usr/bin/env python3
"""Static check for Sky World's fluid policy and cloud height.

The Gradle build does not parse worldgen JSON, so registry load at world creation is
the first thing that would catch a mistake here — after the client is already up. This
walks the files by hand against the 1.21.1 codec field sets instead.

Run from anywhere:  python mod-030-sky-world/tools/check_fluid_policy.py
Exit code 0 = all checks pass.

WHAT THIS FILE ENCODES, AND WHY
-------------------------------
Surface water on floating islands went through six rounds of rejection before landing.
The rules below are the residue of those rounds, so that the next island world does not
repeat them:

1. Fluid features that place a source inside a wall (the `spring_*` family) spill off an
   island rim and fall forever, because there is no ground to land on. They must be both
   excluded in the worldshape AND neutralised with a data/minecraft override — one is
   not enough, historically because Isekai's ADD phase re-injected excluded features
   (fixed in isekai_api 2.1.0, but the belt-and-braces stays: a datapack that only works
   against one library version is a trap).
2. `minecraft:lake` does NOT need that treatment. It tests the solidity of its own shell
   before writing a single block and returns false when the site cannot hold water, so
   it declines to generate on a thin rim rather than leaking over it.
3. Density is measured against vanilla, not chosen by feel. `lake_lava_surface` is the
   only vanilla feature that puts fluid on the open surface, at one chunk in 200.
4. Custom fluid primitives are a smell. Sky World used `isekai_api:pool` for a while and
   got a mathematically round, unenclosed puddle; vanilla's lake gets an irregular,
   walled one out of the box. If a fluid feature here is not `minecraft:lake`, that is a
   decision that needs stating, not a default to drift into.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src" / "main" / "resources"

# Features that place a fluid source with no basin around it. Each must appear in the
# worldshape exclusions AND be neutralised by a data/minecraft placed_feature override.
LEAKING = [
    "minecraft:spring_water",
    "minecraft:spring_lava",
    "minecraft:spring_lava_frozen",
    "minecraft:lake_lava_underground",  # a cave feature; this world excludes all carvers
]

# Vanilla's only open-surface fluid feature fires in one chunk out of this many.
VANILLA_SURFACE_LAKE_RARITY = 200
# No ocean here, so surface lakes carry the whole water supply. That earns a multiple of
# vanilla's density, but a bounded one: 1/8 read as "too many", 1/48 as "maybe too few".
NO_OCEAN_DENSITY_FACTOR = 16

HEIGHTMAPS = {
    "WORLD_SURFACE_WG",
    "WORLD_SURFACE",
    "OCEAN_FLOOR_WG",
    "OCEAN_FLOOR",
    "MOTION_BLOCKING",
    "MOTION_BLOCKING_NO_LEAVES",
}

errors: list[str] = []
notes: list[str] = []


def err(msg: str) -> None:
    errors.append(msg)


def load(rel: str):
    p = RES / rel
    if not p.exists():
        err(f"missing file: {rel}")
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"{rel}: invalid JSON: {e}")
        return None


def check_lake_configured(rel: str) -> None:
    """The water lake. Vanilla ships no surface water lake in 1.21, so this is the one
    fluid feature Sky World defines itself — and it is vanilla's own feature type with a
    different fluid, not a new primitive."""
    obj = load(rel)
    if obj is None:
        return
    if obj.get("type") != "minecraft:lake":
        err(
            f"{rel}: type is {obj.get('type')!r}, not minecraft:lake. A custom fluid "
            "feature has to justify itself against LakeFeature's shell-solidity test — "
            "see this file's header"
        )
        return
    cfg = obj.get("config", {})
    if set(cfg) != {"barrier", "fluid"}:
        err(f"{rel}: config fields {sorted(cfg)} != ['barrier', 'fluid']")
    for key in ("barrier", "fluid"):
        prov = cfg.get(key, {})
        if prov.get("type") != "minecraft:simple_state_provider":
            err(f"{rel}: {key} should be a minecraft:simple_state_provider")
    fluid_state = cfg.get("fluid", {}).get("state", {})
    if fluid_state.get("Properties", {}).get("level") != "0":
        err(f"{rel}: fluid must be a source block (level 0), not flowing")
    # barrier is what walls the basin. Without it the lake is a hole full of water whose
    # sides are whatever the terrain happened to be — the "edge isn't enclosed" symptom.
    if not cfg.get("barrier", {}).get("state", {}).get("Name"):
        err(f"{rel}: barrier has no block — the basin would have no lining")


def check_lake_placed(rel: str, feature: str) -> None:
    obj = load(rel)
    if obj is None:
        return
    if obj.get("feature") != feature:
        err(f"{rel}: feature must be {feature}")
    mods = obj.get("placement", [])
    types = [m.get("type") for m in mods]

    # Vanilla's lake_lava_surface placement, verbatim except for the chance. Anything
    # extra is a knob that was added by feel rather than copied from a working example.
    expected = [
        "minecraft:rarity_filter",
        "minecraft:in_square",
        "minecraft:heightmap",
        "minecraft:biome",
    ]
    if types != expected:
        err(
            f"{rel}: placement is {types}, expected vanilla lake_lava_surface's shape "
            f"{expected}. LakeFeature does its own siting check; a slope filter or an "
            f"offset on top of it is redundant at best"
        )
        return

    chance = mods[0].get("chance")
    floor = VANILLA_SURFACE_LAKE_RARITY // NO_OCEAN_DENSITY_FACTOR
    if not (isinstance(chance, int) and chance >= 1):
        err(f"{rel}: rarity_filter chance must be a positive int")
    elif chance < floor:
        err(
            f"{rel}: rarity_filter chance {chance} — vanilla puts visible surface water "
            f"at 1/{VANILLA_SURFACE_LAKE_RARITY}; even allowing "
            f"{NO_OCEAN_DENSITY_FACTOR}x for having no ocean, {chance} is too dense"
        )
    else:
        notes.append(f"{rel}: one attempt per {chance} chunks")

    if mods[2].get("heightmap") not in HEIGHTMAPS:
        err(f"{rel}: unknown heightmap {mods[2].get('heightmap')!r}")


def descriptors(node):
    """Every worldshape descriptor in a file — sky.json has one, sky_c.json one per layer."""
    if isinstance(node, dict):
        if "applies_to" in node and "exclusions" in node:
            yield node
        for v in node.values():
            yield from descriptors(v)
    elif isinstance(node, list):
        for v in node:
            yield from descriptors(v)


def check_exclusions() -> None:
    """Every leaking feature excluded in every descriptor, and the comparison datapacks
    kept in step with the shipping one — a pack that only changes sky colour must not
    quietly change fluid behaviour too."""
    files = [
        "data/sky_world/isekai/worldshape/sky.json",
        "datapacks/skycolor_b/data/sky_world/isekai/worldshape/sky_b.json",
        "datapacks/skycolor_c/data/sky_world/isekai/layered_worldshape/sky_c.json",
    ]
    for rel in files:
        obj = load(rel)
        if obj is None:
            continue
        found = list(descriptors(obj))
        if not found:
            err(f"{rel}: no worldshape descriptor found")
            continue
        for i, desc in enumerate(found):
            feats = desc.get("exclusions", {}).get("features", [])
            for leak in LEAKING:
                if leak not in feats:
                    err(f"{rel} [descriptor {i}]: {leak} is not excluded")
            if "minecraft:lake_lava_surface" in feats:
                err(
                    f"{rel} [descriptor {i}]: lake_lava_surface is excluded, but "
                    "LakeFeature declines unsuitable sites on its own — excluding it "
                    "removes surface lava for no reason"
                )


def check_overrides() -> None:
    """The data/minecraft neutralisations. count:0 also strips the HeightRangePlacement,
    which is what kept these out of the ore-remap ADD phase before isekai_api 2.1.0
    fixed the re-injection. Keeping it costs nothing and survives a library downgrade.
    """
    for leak in LEAKING:
        name = leak.split(":", 1)[1]
        rel = f"data/minecraft/worldgen/placed_feature/{name}.json"
        obj = load(rel)
        if obj is None:
            continue
        mods = obj.get("placement", [])
        if len(mods) != 1 or mods[0].get("type") != "minecraft:count":
            err(f"{rel}: override should be a single minecraft:count")
            continue
        if mods[0].get("count") != 0:
            err(f"{rel}: count must be 0 to neutralise the feature")
    stray = RES / "data/minecraft/worldgen/placed_feature/lake_lava_surface.json"
    if stray.exists():
        err(
            "data/minecraft/worldgen/placed_feature/lake_lava_surface.json still "
            "overrides vanilla — surface lava lakes are wanted now"
        )


def check_cloud() -> None:
    """The cloud plane has to clear the top island band, or the sheet cuts through rock."""
    # Search the client package rather than a fixed file: the constant moved once
    # already, and a checker that silently stops finding it is worse than none.
    hits = [
        (f, m)
        for f in (ROOT / "src/main/java").rglob("*.java")
        for m in [re.search(r"CLOUD_LEVEL\s*=\s*([0-9.]+)F", f.read_text(encoding="utf-8"))]
        if m
    ]
    if len(hits) != 1:
        err(f"expected exactly one CLOUD_LEVEL constant, found {len(hits)}")
        return
    m = hits[0][1]
    cloud = float(m.group(1))
    ns = load("data/minecraft/worldgen/noise_settings/overworld.json")
    if ns is None:
        return
    tops = [int(x) for x in re.findall(r'"active_max_y":\s*(-?\d+)', json.dumps(ns))]
    if not tops:
        err("overworld.json: no band_density active_max_y found")
        return
    top = max(tops)
    if cloud <= top:
        err(
            f"CLOUD_LEVEL {cloud:.0f} is not above the top island band ceiling {top} — "
            "the cloud sheet will cut through island rock again"
        )
    else:
        notes.append(
            f"cloud plane {cloud:.0f} clears the top band ceiling {top} "
            f"by {cloud - top:.0f} blocks"
        )


def main() -> int:
    check_lake_configured("data/sky_world/worldgen/configured_feature/lake_water.json")
    check_lake_placed(
        "data/sky_world/worldgen/placed_feature/lake_water.json", "sky_world:lake_water"
    )
    check_exclusions()
    check_overrides()
    check_cloud()

    for n in notes:
        print("note:", n)
    if errors:
        print(f"\nFAIL ({len(errors)})")
        for e in errors:
            print("  -", e)
        return 1
    print(
        "\nOK: fluid policy consistent across worldshape, comparison packs and vanilla overrides"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
