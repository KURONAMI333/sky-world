#!/usr/bin/env python3
"""Static check for Sky World's fluid policy and cloud height. JSON is not validated by the Gradle build,
so this walks the files by hand against the 1.21.1 codec field sets.

Run from anywhere:  python mod-030-sky-world/tools/check_fluid_policy.py

Field sets and ranges below were read out of the decompiled 1.21.1 sources
(DiskConfiguration / CountPlacement / RandomOffsetPlacement / HeightmapPlacement) and out of
mod-029's SlopeFilterModifier.CODEC. Exit code 0 = all checks pass.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "src" / "main" / "resources"

# Vanilla placed features that leak fluid over an island rim. Every one of them must be both
# excluded in the worldshape and neutralised by a data/minecraft override, because Isekai's
# ADD phase re-injects any excluded feature that carries a HeightRangePlacement (see report).
LEAKING = [
    "minecraft:spring_water",
    "minecraft:spring_lava",
    "minecraft:spring_lava_frozen",
    "minecraft:lake_lava_surface",
    "minecraft:lake_lava_underground",
]
PONDS = ["sky_world:pond_water", "sky_world:pond_lava"]

HEIGHTMAPS = {
    "WORLD_SURFACE_WG",
    "WORLD_SURFACE",
    "OCEAN_FLOOR_WG",
    "OCEAN_FLOOR",
    "MOTION_BLOCKING",
    "MOTION_BLOCKING_NO_LEAVES",
}

# Measured from vanilla 1.21.1: minecraft:lake_lava_surface is the only feature
# that puts fluid on the open surface, and it fires in one chunk out of this many.
VANILLA_SURFACE_LAKE_RARITY = 200
# This world has no ocean, so surface pools are the only water there is. That earns a
# multiple of vanilla's density, but a bounded one — kura called 1/8 "too many" and
# 1/48 "maybe too few", so the usable band sits around 1/24.
NO_OCEAN_DENSITY_FACTOR = 16
# Files that have already passed a rarity_filter, so a later count is multiplicity
# within one rare site rather than a per-chunk density driver.
seen_rarity: set[str] = set()
# Which shape each placed feature's configured feature turned out to be. The
# surface anchor differs between them, so the placement check needs to know.
FORM: dict[str, str] = {}

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


def check_pool(rel: str, obj: dict) -> int:
    """isekai_api:pool — a carved basin. Returns the maximum xz_radius, or -1.

    The no-spill guarantee is different in kind from the flush-disk one. ``pool``
    carves the disc, lines the rim and floor with ``rim_block``, then fills to the
    rim height, so the fluid is enclosed by construction and its own depth is what
    keeps it below the lip. That makes ``depth`` a safety field, not decoration:
    at depth 0 there is no lip left to hold anything.
    """
    cfg = obj.get("config", {})
    expected = {"fluid", "rim_block", "xz_radius", "depth", "irregularity"}
    if set(cfg) != expected:
        err(f"{rel}: config fields {sorted(cfg)} != {sorted(expected)}")
    fluid = cfg.get("fluid", {})
    if fluid.get("Properties", {}).get("level") != "0":
        err(f"{rel}: fluid must be a source block (level 0), not flowing")
    depth = cfg.get("depth")
    if not (isinstance(depth, int) and 1 <= depth <= 32):
        err(f"{rel}: depth must be 1..32 (codec range); a basin needs a lip")
        return -1
    r = cfg.get("xz_radius", {})
    if r.get("type") != "minecraft:uniform":
        err(
            f"{rel}: xz_radius should be minecraft:uniform — a single fixed size is "
            f"what makes a scatter read as a repeated stamp rather than terrain"
        )
        return -1
    # UniformInt's codec is a MapCodec, so the dispatch puts min/max inline beside
    # "type". A "value" wrapper parses as neither a bare number nor a uniform and
    # kills registry load — accept only the form the game accepts.
    if "value" in r:
        err(
            f"{rel}: xz_radius has a 'value' wrapper — IntProvider dispatch is inline, "
            f'write {{"type":"minecraft:uniform","min_inclusive":N,"max_inclusive":M}}'
        )
        return -1
    lo, hi = r.get("min_inclusive"), r.get("max_inclusive")
    if not (isinstance(lo, int) and isinstance(hi, int) and 1 <= lo <= hi <= 64):
        err(f"{rel}: xz_radius out of the codec range 1..64: {lo}..{hi}")
        return -1
    if lo == hi:
        err(
            f"{rel}: xz_radius is a single value ({lo}) — vary it so the pools do "
            f"not all come out the same size"
        )
    # A pool at irregularity 0 is a compass circle, which is what kura rejected. The
    # feature bites inward only, so the mean radius shrinks by about half the value —
    # xz_radius has to be raised to compensate or the pools come out smaller too.
    irr = cfg.get("irregularity")
    if not isinstance(irr, (int, float)):
        err(f"{rel}: irregularity must be a number")
    elif irr < 0.2:
        err(f"{rel}: irregularity {irr} still reads as a circle — 0.3..0.5 is the band")
    elif irr > 0.6:
        err(f"{rel}: irregularity {irr} looks gnawed rather than natural")
    return hi


def check_disk(rel: str) -> int:
    """Returns the maximum pond radius, or -1 on error.

    Two shapes are accepted, and they are not interchangeable:
    ``minecraft:disk`` paints one flush layer (no basin, reads as a patch on flat
    ground) and ``isekai_api:pool`` carves a real depression. Both are checked for
    the property that actually matters — the fluid cannot escape — but through
    their own invariants.
    """
    obj = load(rel)
    if obj is None:
        return -1
    if obj.get("type") == "isekai_api:pool":
        FORM[rel] = "pool"
        return check_pool(rel, obj)
    FORM[rel] = "disk"
    if obj.get("type") != "minecraft:disk":
        err(f"{rel}: type must be minecraft:disk or isekai_api:pool")
        return -1
    cfg = obj.get("config", {})
    expected = {"state_provider", "target", "radius", "half_height"}
    if set(cfg) != expected:
        err(f"{rel}: config fields {sorted(cfg)} != {sorted(expected)}")
    sp = cfg.get("state_provider", {})
    if set(sp) - {"fallback", "rules"}:
        err(
            f"{rel}: state_provider is a RuleBasedBlockStateProvider (fallback/rules only)"
        )
    if cfg.get("half_height") != 0:
        err(
            f"{rel}: half_height must be 0 — a deeper disk digs a basin that can breach a rim"
        )
    r = cfg.get("radius", {})
    if r.get("type") != "minecraft:uniform":
        err(f"{rel}: radius should be minecraft:uniform")
        return -1
    lo, hi = r.get("min_inclusive"), r.get("max_inclusive")
    if not (isinstance(lo, int) and isinstance(hi, int) and 0 <= lo <= hi <= 8):
        err(f"{rel}: radius out of the codec range 0..8: {lo}..{hi}")
        return -1
    tgt = cfg.get("target", {})
    if tgt.get("type") != "minecraft:matching_blocks":
        err(f"{rel}: target should be minecraft:matching_blocks")
    blocks = tgt.get("blocks")
    # A vanilla HolderSet is either one "#tag" string or a list of plain ids — never a
    # mixed list. Tags keep the target broad enough to actually be reachable (measured
    # against a generated world: 65% of solid columns for water, 12% for lava).
    if not isinstance(blocks, str) or not blocks.startswith("#"):
        err(f"{rel}: target.blocks should be a single '#tag' string, got {blocks!r}")
    elif blocks.startswith("#sky_world:"):
        name = blocks.split(":", 1)[1]
        if not (RES / f"data/sky_world/tags/block/{name}.json").exists():
            err(
                f"{rel}: target.blocks references {blocks} but no such tag file exists "
                f"(expected data/sky_world/tags/block/{name}.json — note 1.21 uses the "
                "singular 'tags/block' directory)"
            )
    return hi


def check_placed(rel: str, feature: str, disk_radius: int) -> None:
    obj = load(rel)
    if obj is None:
        return
    if obj.get("feature") != feature:
        err(f"{rel}: feature must be {feature}")
    mods = obj.get("placement", [])
    types = [m.get("type") for m in mods]
    if "isekai_api:slope_filter" not in types:
        err(
            f"{rel}: no isekai_api:slope_filter — a pond may land on a cliff lip and spill"
        )
    # in_square must precede slope_filter: the filter samples the heightmap at the final x/z.
    if "minecraft:in_square" in types and types.index(
        "minecraft:in_square"
    ) > types.index("isekai_api:slope_filter"):
        err(f"{rel}: minecraft:in_square must come before isekai_api:slope_filter")
    for m in mods:
        t = m.get("type")
        if t == "minecraft:count":
            c = m.get("count")
            lo_hi = (
                (c, c)
                if isinstance(c, int)
                else (
                    (c.get("min_inclusive"), c.get("max_inclusive"))
                    if isinstance(c, dict)
                    else (None, None)
                )
            )
            if not all(isinstance(v, int) and 0 <= v <= 256 for v in lo_hi):
                err(f"{rel}: count {c!r} outside the codec range 0..256")
        elif t == "minecraft:random_offset":
            for k in ("xz_spread", "y_spread"):
                v = m.get(k)
                if not (isinstance(v, int) and -16 <= v <= 16):
                    err(f"{rel}: random_offset.{k} {v!r} outside -16..16")
            # The two shapes anchor differently and the offset has to match, or the
            # feature works one block off. minecraft:disk paints the block it is given,
            # so it needs -1 to reach the surface block itself. isekai_api:pool takes
            # the air cell above the surface as its origin and digs down from there
            # (PoolFeature.place: "origin = air cell above the top solid block"), so
            # shifting it down would sink the whole basin.
            want = 0 if FORM.get(rel) == "pool" else -1
            if m.get("y_spread") != want:
                err(
                    f"{rel}: y_spread must be {want} for a "
                    f"{FORM.get(rel, 'disk')} feature"
                )
        elif t == "minecraft:heightmap":
            if m.get("heightmap") not in HEIGHTMAPS:
                err(f"{rel}: unknown heightmap {m.get('heightmap')!r}")
        elif t == "isekai_api:slope_filter":
            if set(m) - {
                "type",
                "min_slope",
                "max_slope",
                "sample_radius",
                "heightmap",
            }:
                err(
                    f"{rel}: slope_filter has fields outside SlopeFilterModifier.CODEC: {sorted(m)}"
                )
            sr = m.get("sample_radius", 2)
            if not (isinstance(sr, int) and 1 <= sr <= 8):
                err(f"{rel}: sample_radius {sr!r} outside the codec range 1..8")
            for k in ("min_slope", "max_slope"):
                v = m.get(k)
                if v is not None and not (
                    isinstance(v, (int, float)) and 0.0 <= v <= 1.0
                ):
                    err(f"{rel}: {k} {v!r} outside 0.0..1.0")
            if m.get("heightmap") not in HEIGHTMAPS:
                err(f"{rel}: slope_filter heightmap {m.get('heightmap')!r} unknown")
            # The spill invariant: the flatness test must reach further than the pond does.
            if disk_radius >= 0 and sr <= disk_radius:
                err(
                    f"{rel}: sample_radius ({sr}) must exceed the disk radius ({disk_radius}) — "
                    "otherwise the filter can pass a spot whose pond still touches the rim"
                )
            # slope = min(1, maxDelta / sample_radius); state the block delta this admits.
            ms = m.get("max_slope", 1.0)
            notes.append(
                f"{rel}: slope_filter admits a height delta of at most "
                f"{int(ms * sr)} block(s) at +-{sr} on each cardinal axis"
            )
        elif t == "minecraft:rarity_filter":
            # Density is the whole difference between "a pond" and "a rash of ponds".
            # minecraft:count fires every chunk; rarity_filter fires in one chunk of
            # `chance`. Anything denser than one chunk in four covers the ground.
            c = m.get("chance")
            if set(m) != {"type", "chance"}:
                err(f"{rel}: rarity_filter takes only 'chance'")
            if not (isinstance(c, int) and c >= 1):
                err(f"{rel}: rarity_filter chance must be a positive int")
            elif c < VANILLA_SURFACE_LAKE_RARITY // NO_OCEAN_DENSITY_FACTOR:
                # Anchor, not taste: vanilla's own visible surface water
                # (minecraft:lake_lava_surface) is one chunk in 200. Islands cover a
                # fraction of the chunks here so some multiple of that is defensible,
                # but an order of magnitude denser is a rash, not a landscape.
                err(
                    f"{rel}: rarity_filter chance {c} — vanilla puts visible surface "
                    f"water at 1/{VANILLA_SURFACE_LAKE_RARITY}; even allowing "
                    f"{NO_OCEAN_DENSITY_FACTOR}x for having no ocean, {c} is too dense"
                )
            else:
                notes.append(f"{rel}: one attempt per {c} chunks")
            seen_rarity.add(rel)
        elif t == "minecraft:count":
            # count multiplies whatever reached it. Ahead of a rarity_filter it is the
            # density driver and fires every chunk; behind one it is how a single
            # already-rare site gets several overlapping discs, which is what stops
            # the pool from reading as a mathematical circle.
            if rel not in seen_rarity:
                err(
                    f"{rel}: minecraft:count fires in every chunk — put a "
                    "minecraft:rarity_filter ahead of it"
                )
            else:
                cnt = m.get("count")
                hi = cnt.get("max_inclusive") if isinstance(cnt, dict) else cnt
                if isinstance(hi, int) and hi > 4:
                    err(f"{rel}: count max {hi} per site is a cluster, not a pond")
                else:
                    notes.append(f"{rel}: {cnt} overlapping discs per site")
        elif t in ("minecraft:in_square", "minecraft:biome"):
            if set(m) != {"type"}:
                err(f"{rel}: {t} takes no fields")
        else:
            err(f"{rel}: unreviewed placement modifier {t!r}")


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


def check_worldshapes() -> None:
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
        for i, d in enumerate(found):
            where = f"{rel}[descriptor {i}]"
            excl = d.get("exclusions", {}).get("features", [])
            for k in LEAKING:
                if k not in excl:
                    err(f"{where}: exclusions.features is missing {k}")
            if "additions" in d:
                err(
                    f"{where}: ponds are injected by the neoforge:add_features biome modifier, "
                    "not by worldshape additions — two paths would place every pond twice"
                )


def check_biome_modifier() -> None:
    """The ponds are injected by NeoForge's own biome modifier, not by the worldshape.

    Isekai's additions path needs a live server context at modify time; the NeoForge modifier
    has no such dependency, and E2 (a reachable water source) must not hinge on that timing.
    One file also beats six descriptor copies across the two comparison datapacks.
    """
    rel = "data/sky_world/neoforge/biome_modifier/add_ponds.json"
    obj = load(rel)
    if obj is None:
        return
    if obj.get("type") != "neoforge:add_features":
        err(f"{rel}: type must be neoforge:add_features")
    if obj.get("biomes") != "#minecraft:is_overworld":
        err(
            f"{rel}: biomes must be #minecraft:is_overworld to match the worldshape's applies_to"
        )
    feats = obj.get("features", [])
    for p in PONDS:
        if p not in feats:
            err(f"{rel}: features is missing {p}")
    if obj.get("step") != "lakes":
        err(
            f"{rel}: step is {obj.get('step')!r}; must be 'lakes' so vegetation generates after "
            "the water and never floats over it"
        )


def check_neutralised() -> None:
    for key in LEAKING:
        name = key.split(":", 1)[1]
        rel = f"data/minecraft/worldgen/placed_feature/{name}.json"
        obj = load(rel)
        if obj is None:
            continue
        mods = obj.get("placement", [])
        if (
            len(mods) != 1
            or mods[0].get("type") != "minecraft:count"
            or mods[0].get("count") != 0
        ):
            err(f"{rel}: must be exactly one minecraft:count with count 0")
        if "HeightRangePlacement" in json.dumps(obj) or any(
            m.get("type") == "minecraft:height_range" for m in mods
        ):
            err(
                f"{rel}: must not carry a height_range — that is what makes Isekai's ADD phase "
                "rebuild and re-inject it"
            )


def check_cloud_above_bands() -> None:
    """The cloud plane must clear the highest island band.

    Vanilla's 192 cut through the middle band, which is the defect this replaces. The band
    ceilings live in the noise settings and are edited independently of the client class, so
    assert the coupling here rather than discovering it in a screenshot.
    """
    java = (
        ROOT
        / "src/main/java/com/kuronami/skyworld/client/SkyWorldDimensionEffects.java"
    )
    if not java.exists():
        err("missing SkyWorldDimensionEffects.java")
        return
    m = re.search(r"CLOUD_LEVEL\s*=\s*([0-9.]+)F", java.read_text(encoding="utf-8"))
    if not m:
        err("SkyWorldDimensionEffects: could not read CLOUD_LEVEL")
        return
    cloud = float(m.group(1))
    ns = load("data/minecraft/worldgen/noise_settings/overworld.json")
    if ns is None:
        return
    tops = [int(v) for v in re.findall(r'"active_max_y":\s*(-?\d+)', json.dumps(ns))]
    if not tops:
        err(
            "noise_settings/overworld.json: no active_max_y found — band layout changed shape"
        )
        return
    top = max(tops)
    if cloud <= top:
        err(
            f"CLOUD_LEVEL {cloud} is not above the top island band ceiling {top} — "
            "the cloud sheet will cut through island rock again"
        )
    else:
        notes.append(
            f"cloud plane {cloud:.0f} clears the top band ceiling {top} "
            f"by {cloud - top:.0f} blocks"
        )


def main() -> int:
    cf = "data/sky_world/worldgen/configured_feature/{}.json"
    pf = "data/sky_world/worldgen/placed_feature/{}.json"
    rw = check_disk("data/sky_world/worldgen/configured_feature/pond_water.json")
    rl = check_disk("data/sky_world/worldgen/configured_feature/pond_lava.json")
    for n in ("pond_water", "pond_lava"):
        FORM[pf.format(n)] = FORM.get(cf.format(n), "disk")
    check_placed(
        "data/sky_world/worldgen/placed_feature/pond_water.json",
        "sky_world:pond_water",
        rw,
    )
    check_placed(
        "data/sky_world/worldgen/placed_feature/pond_lava.json",
        "sky_world:pond_lava",
        rl,
    )
    check_worldshapes()
    check_biome_modifier()
    check_cloud_above_bands()
    check_neutralised()

    for n in notes:
        print("note: " + n)
    if errors:
        print(f"\nFAIL ({len(errors)}):")
        for e in errors:
            print("  - " + e)
        return 1
    print(
        "\nOK: fluid policy consistent across worldshape, comparison packs and vanilla overrides"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
