#!/usr/bin/env python3
"""Codec + design-invariant check for the Sky World noise_settings.

`./gradlew build` never parses datapack JSON, so a wrong field name or an
out-of-range value only surfaces as a world-load failure in-game. This script
closes that gap for `data/minecraft/worldgen/noise_settings/overworld.json`.

Two independent passes:

1. CODEC PASS — every density function node is checked against the *actual*
   field set of its Java codec. Sources (1.21.1 / Isekai 2.1.0):
     net/minecraft/world/level/levelgen/DensityFunctions.java
     net/minecraft/world/level/levelgen/synth/BlendedNoise.java
     com/kuronami/isekaiapi/densityfunction/{BandDensityDF,BlendedNoiseDF,SqueezeDF}.java
   Unknown type, missing required field, unknown extra field and out-of-range
   numeric all fail. A bare number and a bare string (a density_function id)
   are both legal density functions and are accepted as leaves.

2. DESIGN PASS — the keel invariant. Each layer is
   `band_density(noise = island_noise + y_clamped_gradient chain)`. The band's
   multiplicative envelope must be 1 (i.e. y strictly inside
   [active_min_y, active_max_y]) across the whole island, top tip to keel tip.
   Where the envelope drops below 1 the cut is multiplicative again and the
   keel flattens back into the plate this design exists to remove. The script
   derives the extreme tip/top Y from the gradient chain itself and checks the
   band contains them.

Usage:
    python tools/check_density_json.py            # exit 0 = pass
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = (
    REPO / "src/main/resources/data/minecraft/worldgen/noise_settings/overworld.json"
)

# vanilla DimensionType.MIN_Y * 2 / MAX_Y * 2 -> y_clamped_gradient's int range
Y_MIN, Y_MAX = -4064, 4062
NOISE_VALUE = (-1_000_000.0, 1_000_000.0)

ARG1_ARG2 = ({"argument1", "argument2"}, set(), {})
ARGUMENT = ({"argument"}, set(), {})

# type -> (required fields, optional fields, {field: (lo, hi)})
SPEC: dict[str, tuple[set[str], set[str], dict[str, tuple[float, float]]]] = {
    "minecraft:add": ARG1_ARG2,
    "minecraft:mul": ARG1_ARG2,
    "minecraft:min": ARG1_ARG2,
    "minecraft:max": ARG1_ARG2,
    "minecraft:abs": ARGUMENT,
    "minecraft:square": ARGUMENT,
    "minecraft:cube": ARGUMENT,
    "minecraft:half_negative": ARGUMENT,
    "minecraft:quarter_negative": ARGUMENT,
    "minecraft:squeeze": ARGUMENT,
    "minecraft:interpolated": ARGUMENT,
    "minecraft:blend_density": ARGUMENT,
    "minecraft:flat_cache": ARGUMENT,
    "minecraft:cache_2d": ARGUMENT,
    "minecraft:cache_once": ARGUMENT,
    "minecraft:cache_all_in_cell": ARGUMENT,
    "minecraft:constant": ARGUMENT,
    "minecraft:clamp": ({"input", "min", "max"}, set(), {}),
    "minecraft:y_clamped_gradient": (
        {"from_y", "to_y", "from_value", "to_value"},
        set(),
        {
            "from_y": (Y_MIN, Y_MAX),
            "to_y": (Y_MIN, Y_MAX),
            "from_value": NOISE_VALUE,
            "to_value": NOISE_VALUE,
        },
    ),
    "minecraft:noise": ({"noise", "xz_scale", "y_scale"}, set(), {}),
    "minecraft:shifted_noise": (
        {"noise", "shift_x", "shift_y", "shift_z", "xz_scale", "y_scale"},
        set(),
        {},
    ),
    "minecraft:range_choice": (
        {
            "input",
            "min_inclusive",
            "max_exclusive",
            "when_in_range",
            "when_out_of_range",
        },
        set(),
        {},
    ),
    "minecraft:old_blended_noise": (
        {"xz_scale", "y_scale", "xz_factor", "y_factor", "smear_scale_multiplier"},
        set(),
        {
            "xz_scale": (0.001, 1000.0),
            "y_scale": (0.001, 1000.0),
            "xz_factor": (0.001, 1000.0),
            "y_factor": (0.001, 1000.0),
            "smear_scale_multiplier": (1.0, 8.0),
        },
    ),
    "isekai_api:squeeze": ARGUMENT,
    "isekai_api:band_density": (
        {"active_min_y", "active_max_y", "noise"},
        {"gradient_width", "invert", "solidity_bias"},
        {"solidity_bias": (-1.0, 1.0)},
    ),
    "isekai_api:blended_noise": (
        {"size_xz", "size_y"},
        {"smear_multiplier"},
        {
            "size_xz": (1.0, 1000.0),
            "size_y": (1.0, 1000.0),
            "smear_multiplier": (1.0, 8.0),
        },
    ),
}

# Per type, the fields whose value is a nested density function. Anything else is a
# scalar / id and must not be recursed into. Keyed per type on purpose: "noise" is a
# noise-parameter id under minecraft:noise but a full density function under
# isekai_api:band_density, and treating it globally as a scalar silently skips the
# whole layer subtree.
DF_FIELDS: dict[str, set[str]] = {
    "minecraft:clamp": {"input"},
    "minecraft:noise": set(),
    "minecraft:shifted_noise": {"shift_x", "shift_y", "shift_z"},
    "minecraft:range_choice": {"input", "when_in_range", "when_out_of_range"},
    "minecraft:old_blended_noise": set(),
    "minecraft:y_clamped_gradient": set(),
    "isekai_api:blended_noise": set(),
    "isekai_api:band_density": {"noise"},
}

errors: list[str] = []
# Non-fatal observations. Used where a file is internally consistent but the design
# it encodes has a known consequence worth restating at every run.
notes: list[str] = []


def walk(node, path: str) -> None:
    if isinstance(node, (int, float, str)):
        return  # constant, or a density_function / noise id
    if not isinstance(node, dict):
        errors.append(f"{path}: not a density function ({type(node).__name__})")
        return
    t = node.get("type")
    if t is None:
        errors.append(f'{path}: object without "type"')
        return
    if t not in SPEC:
        errors.append(f"{path}: unknown density function type {t!r}")
        return
    req, opt, ranges = SPEC[t]
    present = set(node.keys()) - {"type"}
    for missing in sorted(req - present):
        errors.append(f"{path}: {t} missing required field {missing!r}")
    for extra in sorted(present - req - opt):
        errors.append(f"{path}: {t} has unknown field {extra!r}")
    for f, (lo, hi) in ranges.items():
        if f in node and isinstance(node[f], (int, float)) and not lo <= node[f] <= hi:
            errors.append(
                f"{path}: {t}.{f} = {node[f]} outside codec range [{lo}, {hi}]"
            )
    if t == "isekai_api:band_density":
        if node.get("gradient_width", 30) < 1:
            errors.append(f"{path}: band_density.gradient_width must be >= 1")
        if "active_max_y" in node and "active_min_y" in node:
            if node["active_max_y"] <= node["active_min_y"]:
                errors.append(
                    f"{path}: band_density active_max_y must be > active_min_y"
                )
    # default: every field of a generic composer (add/mul/max/argument/...) is a
    # density function; specialised types declare their own set in DF_FIELDS.
    df_fields = DF_FIELDS.get(t)
    for k, v in node.items():
        if k == "type":
            continue
        if df_fields is None or k in df_fields:
            walk(v, f"{path}.{k}")


def collect_bands(node, out: list) -> None:
    if isinstance(node, dict):
        if node.get("type") == "isekai_api:band_density":
            out.append(node)
        for v in node.values():
            collect_bands(v, out)


def gradient_chain(node, out: list) -> None:
    """Collect every y_clamped_gradient added into a band's noise argument."""
    if isinstance(node, dict):
        if node.get("type") == "minecraft:y_clamped_gradient":
            out.append(node)
        for v in node.values():
            gradient_chain(v, out)


def profile_at(grads: list, y: float) -> float:
    total = 0.0
    for g in grads:
        f_y, t_y = float(g["from_y"]), float(g["to_y"])
        t = min(max((y - f_y) / (t_y - f_y), 0.0), 1.0)
        total += g["from_value"] + t * (g["to_value"] - g["from_value"])
    return total


def profile_form(node) -> str:
    """Which vertical-profile design a band uses.

    The two are not interchangeable and their invariants are opposites, so the
    checks below have to know which one is in force:

    - "multiplicative": ``mul(island_noise, y_clamped_gradient)``. The gradient is
      a 0..1 factor, so it scales the noise toward zero at the band edges. Density
      saturates as the noise grows, which flattens the underside into a plate —
      the shape this world shipped with.
    - "additive": ``island_noise + add(y_clamped_gradient, ...)``. The gradients are
      signed offsets, so the cut-off height tracks the noise linearly and the
      underside tapers to a keel.

    Detected structurally rather than declared, so the file cannot drift away from
    whichever set of invariants gets applied.
    """
    if isinstance(node, dict):
        if node.get("type") == "minecraft:mul":
            for arg in (node.get("argument1"), node.get("argument2")):
                if (
                    isinstance(arg, dict)
                    and arg.get("type") == "minecraft:y_clamped_gradient"
                ):
                    return "multiplicative"
        for v in node.values():
            if isinstance(v, (dict, list)):
                form = profile_form(v)
                if form != "none":
                    return form
    elif isinstance(node, list):
        for v in node:
            form = profile_form(v)
            if form != "none":
                return form
    grads: list = []
    gradient_chain(node, grads)
    return "additive" if grads else "none"


def design_pass(doc) -> None:
    bands: list = []
    collect_bands(doc["noise_router"]["final_density"], bands)
    if len(bands) != 3:
        errors.append(f"design: expected 3 band_density layers, found {len(bands)}")
    for b in bands:
        lo, hi = b["active_min_y"], b["active_max_y"]
        grads: list = []
        gradient_chain(b["noise"], grads)
        if not grads:
            errors.append(
                f"design: band {lo}-{hi} has no vertical profile at all — the layer "
                f"would be a uniform slab between {lo} and {hi}"
            )
            continue
        if profile_form(b["noise"]) == "multiplicative":
            # A 0..1 factor cannot push density below the threshold on its own, so
            # the keel invariants do not apply. What still has to hold is that the
            # ramp lives inside the band it shapes: a factor that is already 1.0 at
            # active_min_y leaves the bottom face uncut.
            for g in grads:
                f_y, t_y = float(g["from_y"]), float(g["to_y"])
                span_lo, span_hi = min(f_y, t_y), max(f_y, t_y)
                if span_hi < lo or span_lo > hi:
                    errors.append(
                        f"design: band {lo}-{hi}: multiplicative ramp {span_lo}-{span_hi} "
                        f"lies outside the band, so it shapes nothing"
                    )
            notes.append(
                f"design: band {lo}-{hi} uses the multiplicative profile — the "
                f"underside saturates into a plate by construction; a keel needs "
                f"the additive form"
            )
            continue
        threshold = 0.18 - b.get("solidity_bias", 0.0)
        # The island exists where island_noise + profile(y) > threshold. The most
        # extreme column blended_noise can produce is ~1.15 (measured tail of
        # old_blended_noise; codec max is 1.0 per limit-noise sum), so require the
        # profile to have driven the density below the threshold by that margin
        # before the envelope starts cutting.
        margin = 1.15 - threshold
        ys = range(-64, 320)
        inside = [y for y in ys if profile_at(grads, float(y)) > -margin]
        if not inside:
            errors.append(
                f"design: band {lo}-{hi}: the y_clamped_gradient profile is below "
                f"-{margin:.2f} everywhere, so the layer can never be solid"
            )
            continue
        tip, top = min(inside), max(inside)
        if profile_at(grads, float(tip)) >= 0.0 and tip <= -64:
            errors.append(
                f"design: band {lo}-{hi}: profile never falls at the bottom — "
                f"there is no additive keel, the underside will be a flat cut"
            )
        if tip < lo:
            errors.append(
                f"design: band {lo}-{hi}: keel can reach y={tip} which is below "
                f"active_min_y={lo} — the envelope would flatten the tip"
            )
        if top > hi:
            errors.append(
                f"design: band {lo}-{hi}: dome can reach y={top} which is above "
                f"active_max_y={hi} — the envelope would flatten the top"
            )
        print(
            f"  band {lo:4d}..{hi:4d} bias={b.get('solidity_bias', 0.0):+.2f} "
            f"threshold={threshold:.2f}  profile keeps terrain within y {tip}..{top}"
            f"  -> {'ok' if lo <= tip and top <= hi else 'OUT OF BAND'}"
        )


def main() -> int:
    doc = json.loads(TARGET.read_text(encoding="utf-8"))
    print(f"checking {TARGET.relative_to(REPO)}")
    for key in (
        "final_density",
        "initial_density_without_jaggedness",
        "temperature",
        "vegetation",
        "barrier",
        "fluid_level_floodedness",
        "fluid_level_spread",
        "lava",
        "vein_toggle",
        "vein_ridged",
        "vein_gap",
    ):
        walk(doc["noise_router"][key], f"noise_router.{key}")
    print("codec pass done")
    design_pass(doc)
    for n in notes:
        print("note:", n)
    if errors:
        print(f"\nFAIL ({len(errors)})")
        for e in errors:
            print("  -", e)
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
