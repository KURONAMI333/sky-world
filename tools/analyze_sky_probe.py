#!/usr/bin/env python3
"""probe_sky_ores.py の出力（per-chunk × per-Y-slice のブロック数）を読む。

出す表は3つ:
  --profile   Y スライスごとの岩体積と鉱石密度（帯の実体をここで確認する）
  --bands     指定した Y 帯ごとの密度。複数ファイルを並べて比較できる
  --topmost   同一帯の中で「上に島がある列」と「無い列」の鉱石密度を比べる
              （帯をまたいだ密度勾配は Y 依存の供給差と交絡するので使わない）
"""

from __future__ import annotations

import argparse
import json
import sys

STONE_FAMILY = {
    "minecraft:stone",
    "minecraft:andesite",
    "minecraft:granite",
    "minecraft:diorite",
    "minecraft:tuff",
    "minecraft:deepslate",
    "minecraft:coal_ore",
    "minecraft:iron_ore",
    "minecraft:copper_ore",
    "minecraft:deepslate_coal_ore",
    "minecraft:deepslate_iron_ore",
}
SHOW = [
    "minecraft:andesite",
    "minecraft:granite",
    "minecraft:diorite",
    "minecraft:coal_ore",
    "minecraft:iron_ore",
    "minecraft:copper_ore",
]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cell_band(d, cell, bi):
    return d["cells"][cell][str(bi)]


def rock(counts):
    return sum(v for k, v in counts.items() if k in STONE_FAMILY)


def agg(d, band_idxs, cells=None):
    tot = {b: 0 for b in d["blocks"]}
    for cell in (cells if cells is not None else d["cells"]):
        for bi in band_idxs:
            for b, v in cell_band(d, cell, bi).items():
                tot[b] += v
    return tot


def ppm(tot, block):
    r = rock(tot)
    return 1e6 * tot.get(block, 0) / r if r else 0.0


def cmd_profile(d):
    print(f"\n=== {d['label']}: Y スライス別 ===")
    print(
        f"{'Y':>10}{'rock':>10}" + "".join(f"{b.split(':')[1][:9]:>10}" for b in SHOW)
    )
    for bi, (lo, hi) in enumerate(d["bands"]):
        tot = agg(d, [bi])
        r = rock(tot)
        print(f"{lo:>4}..{hi:<5}{r:>10}" + "".join(f"{tot.get(b,0):>10}" for b in SHOW))


def cmd_bands(datasets, bands_spec):
    """bands_spec: 'name=lo:hi,name=lo:hi' — probe の Y スライスを束ねて集計する。"""
    groups = []
    for part in bands_spec.split(","):
        name, rng = part.split("=")
        lo, hi = (int(v) for v in rng.split(":"))
        groups.append((name, lo, hi))
    for name, lo, hi in groups:
        print(f"\n=== 帯 {name}  Y {lo}..{hi} ===")
        print(
            f"{'dataset':<22}{'rock':>10}"
            + "".join(f"{b.split(':')[1][:9]:>11}" for b in SHOW)
        )
        for d in datasets:
            idxs = [
                i for i, (blo, bhi) in enumerate(d["bands"]) if blo >= lo and bhi <= hi
            ]
            tot = agg(d, idxs)
            r = rock(tot)
            print(
                f"{d['label']:<22}{r:>10}"
                + "".join(f"{tot.get(b,0):>6}/{ppm(tot,b):>4.0f}" for b in SHOW)
            )
        print("   (値は 実数/百万岩ブロックあたり)")


def cmd_topmost(d, band_spec, min_rock):
    """同一帯の中で、上位帯に島がある列と無い列の鉱石密度を比べる。"""
    name, rng = band_spec.split("=")
    lo, hi = (int(v) for v in rng.split(":"))
    idxs = [i for i, (blo, bhi) in enumerate(d["bands"]) if blo >= lo and bhi <= hi]
    above = [i for i, (blo, _) in enumerate(d["bands"]) if blo > hi]

    with_above, without_above = [], []
    for cell in d["cells"]:
        r_here = rock(agg(d, idxs, [cell]))
        if r_here < min_rock:
            continue
        r_above = rock(agg(d, above, [cell]))
        (with_above if r_above >= min_rock else without_above).append(cell)

    print(
        f"\n=== {d['label']}: 帯 {name} (Y {lo}..{hi}) の列を、上に島があるかで分ける ==="
    )
    print(
        f"  上に島あり: {len(with_above)} chunk / 上に島なし: {len(without_above)} chunk"
        f"   (島の判定 = 岩 >= {min_rock} ブロック)"
    )
    print(
        f"{'群':<16}{'rock':>10}" + "".join(f"{b.split(':')[1][:9]:>11}" for b in SHOW)
    )
    for label, cells in (("上に島あり", with_above), ("上に島なし", without_above)):
        if not cells:
            print(f"{label:<16}  (該当なし)")
            continue
        tot = agg(d, idxs, cells)
        print(
            f"{label:<16}{rock(tot):>10}"
            + "".join(f"{tot.get(b,0):>6}/{ppm(tot,b):>4.0f}" for b in SHOW)
        )
    print("   (値は 実数/百万岩ブロックあたり)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--bands", default="")
    ap.add_argument("--topmost", default="")
    ap.add_argument("--min-rock", type=int, default=200)
    args = ap.parse_args()

    datasets = [load(f) for f in args.files]
    if args.profile:
        for d in datasets:
            cmd_profile(d)
    if args.bands:
        cmd_bands(datasets, args.bands)
    if args.topmost:
        for d in datasets:
            cmd_topmost(d, args.topmost, args.min_rock)
    return 0


if __name__ == "__main__":
    sys.exit(main())
