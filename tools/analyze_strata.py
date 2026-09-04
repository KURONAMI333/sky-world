#!/usr/bin/env python3
"""深層岩の帯（`isekai_api:strata`）の深さ N を、候補どうしで比べるための表を出す。

probe_sky_ores.py の出力（per-chunk × per-Y-slice のブロック数）を読み、帯ごとに

  * 島の断面（表層の1列あたり 草／土／石／深層岩が何ブロックか）
  * 島の岩体積のうち深層岩が占める割合
  * 深層岩が1ブロックも無い島の割合
  * deepslate_* 鉱石変種の実数

を並べる。島の単位は (チャンク, 帯) のセルで、岩が `--min-rock` 以上あるものだけを島と
数える。1チャンクに島が2つ縦に並ぶ帯ではそれを1つと数えるので、「深層岩が無い島」は
薄い島の割合の下限として読む。

Usage:
    python tools/analyze_strata.py run/probe-results/strata_n{8,12,16}.json \
        --baseline run/probe-results/geode288_walk.json
"""

from __future__ import annotations

import argparse
import json
import sys

# 島の岩体積。石バリアントも鉱石も、元は石か深層岩だったもの。
ROCK = {
    "minecraft:stone",
    "minecraft:deepslate",
    "minecraft:andesite",
    "minecraft:granite",
    "minecraft:diorite",
    "minecraft:tuff",
    "minecraft:coal_ore",
    "minecraft:iron_ore",
    "minecraft:copper_ore",
    "minecraft:deepslate_coal_ore",
    "minecraft:deepslate_iron_ore",
    "minecraft:deepslate_copper_ore",
}
DEEP_ORES = [
    "minecraft:deepslate_coal_ore",
    "minecraft:deepslate_iron_ore",
    "minecraft:deepslate_copper_ore",
]
# 帯は sky.json の3層に対応する（下段/中段/上段）。
GROUPS = [
    ("下段 Y32..111", 32, 111),
    ("中段 Y112..191", 112, 191),
    ("上段 Y208..255", 208, 255),
]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def slice_idx(data, lo, hi):
    return [str(i) for i, (a, b) in enumerate(data["bands"]) if a >= lo and b <= hi]


def cell_totals(data, idxs):
    """(セル -> ブロック別の数) を帯の中で足し合わせる。"""
    out = {}
    for cell, per_band in data["cells"].items():
        t = {}
        for bi in idxs:
            for k, v in per_band[bi].items():
                t[k] = t.get(k, 0) + v
        out[cell] = t
    return out


def report(datasets, min_rock):
    for name, lo, hi in GROUPS:
        print(f"\n=== {name} ===")
        print(
            f"{'run':<14}{'島':>5}{'深層岩なし':>11}"
            f"{'草/列':>8}{'土/列':>8}{'石/列':>8}{'深層岩/列':>11}{'岩計/列':>9}"
            f"{'深層岩の割合':>14}"
            + "".join(f"{o.split(':')[1][10:]:>9}" for o in DEEP_ORES)
        )
        for d in datasets:
            idxs = slice_idx(d, lo, hi)
            cells = cell_totals(d, idxs)
            islands = [
                t for t in cells.values() if sum(t.get(k, 0) for k in ROCK) >= min_rock
            ]
            if not islands:
                print(f"{d['label']:<14}  (島なし)")
                continue
            agg = {}
            for t in islands:
                for k, v in t.items():
                    agg[k] = agg.get(k, 0) + v
            rock = sum(agg.get(k, 0) for k in ROCK)
            deep = agg.get("minecraft:deepslate", 0)
            cols = agg.get("minecraft:grass_block", 0) or 1
            nodeep = sum(1 for t in islands if t.get("minecraft:deepslate", 0) == 0)
            print(
                f"{d['label']:<14}{len(islands):>5}{nodeep:>6} ({100*nodeep/len(islands):>3.0f}%)"
                f"{agg.get('minecraft:grass_block',0)/cols:>8.1f}"
                f"{agg.get('minecraft:dirt',0)/cols:>8.1f}"
                f"{agg.get('minecraft:stone',0)/cols:>8.1f}"
                f"{deep/cols:>11.1f}{rock/cols:>9.1f}"
                f"{100*deep/rock if rock else 0:>13.1f}%"
                + "".join(f"{agg.get(o,0):>9}" for o in DEEP_ORES)
            )
    print(
        "\n（草/土/石/深層岩は表層1列あたりのブロック数＝島の断面。列の数は grass_block で数えている。"
        "\n 深層岩の割合は、その帯の島の岩体積に対する深層岩の比。）"
    )

    print("\n=== 全域（帯を問わない実数） ===")
    keys = [
        "minecraft:stone",
        "minecraft:deepslate",
        *DEEP_ORES,
        "minecraft:coal_ore",
        "minecraft:iron_ore",
        "minecraft:copper_ore",
        "minecraft:dirt",
        "minecraft:grass_block",
    ]
    print(f"{'run':<14}" + "".join(f"{k.split(':')[1][:12]:>14}" for k in keys))
    for d in datasets:
        agg = {}
        for per_band in d["cells"].values():
            for band in per_band.values():
                for k, v in band.items():
                    agg[k] = agg.get(k, 0) + v
        print(f"{d['label']:<14}" + "".join(f"{agg.get(k,0):>14}" for k in keys))

    # 帯を入れても鉱石の総供給は変わらないはず（変種が入れ替わるだけ）。
    # ここが崩れていたら、測っているのは変種の入れ替えではなく別の何か。
    print("\n=== 鉱石の総供給（通常変種 + deepslate 変種）===")
    pairs = [
        ("coal", "minecraft:coal_ore", "minecraft:deepslate_coal_ore"),
        ("iron", "minecraft:iron_ore", "minecraft:deepslate_iron_ore"),
        ("copper", "minecraft:copper_ore", "minecraft:deepslate_copper_ore"),
    ]
    print(f"{'run':<14}" + "".join(f"{n:>12}" for n, _, _ in pairs))
    for d in datasets:
        agg = {}
        for per_band in d["cells"].values():
            for band in per_band.values():
                for k, v in band.items():
                    agg[k] = agg.get(k, 0) + v
        print(
            f"{d['label']:<14}"
            + "".join(f"{agg.get(a,0)+agg.get(b,0):>12}" for _, a, b in pairs)
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--min-rock", type=int, default=200)
    args = ap.parse_args()
    report([load(f) for f in args.files], args.min_rock)
    return 0


if __name__ == "__main__":
    sys.exit(main())
