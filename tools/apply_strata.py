#!/usr/bin/env python3
"""島の断面に深層岩の帯を出し入れする（`isekai_api:strata` を surface_rule に差す）。

surface_rule の sequence は first-match-wins で、`isekai_api:vanilla_overworld_surface`
が上から数えて浅い側（草・土）を先に取る。その次に strata を置くと、上から N ブロック
までを石、その下 64 ブロックを深層岩が取り、残りは今までどおり
`isekai_api:worldshape_default_block` が埋める。

N は「島の上面から数えて深層岩が始まる深さ」。既定値は置かない（未確定）。

Usage:
    python tools/apply_strata.py --n 12     # 深さ 13 から深層岩
    python tools/apply_strata.py --off      # 帯を外す
    python tools/apply_strata.py --show     # いまの sequence を表示
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

NOISE_SETTINGS = (
    pathlib.Path(__file__).resolve().parent.parent
    / "src/main/resources/data/minecraft/worldgen/noise_settings/overworld.json"
)
STRATA = "isekai_api:strata"
ANCHOR = "isekai_api:vanilla_overworld_surface"
DEEPSLATE_THICKNESS = 64  # Band の codec の上限。島の厚みを超えるので実質「以下すべて」


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, help="深層岩が始まる深さ（1..63）")
    ap.add_argument("--off", action="store_true")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    data = json.loads(NOISE_SETTINGS.read_text(encoding="utf-8"))
    seq = data["surface_rule"]["sequence"]

    if args.show:
        for i, e in enumerate(seq):
            extra = f"  bands={[(b[chr(39)+chr(39)] if False else b['block']['Name'], b['thickness']) for b in e['bands']]}" if e["type"] == STRATA else ""
            print(f"{i}: {e['type']}{extra}")
        return 0

    seq = [e for e in seq if e["type"] != STRATA]

    if not args.off:
        if args.n is None or not 1 <= args.n <= 63:
            print("--n は 1..63、または --off", file=sys.stderr)
            return 2
        anchor = next(i for i, e in enumerate(seq) if e["type"] == ANCHOR)
        seq.insert(
            anchor + 1,
            {
                "type": STRATA,
                "bands": [
                    {"block": {"Name": "minecraft:stone"}, "thickness": args.n},
                    {"block": {"Name": "minecraft:deepslate"}, "thickness": DEEPSLATE_THICKNESS},
                ],
            },
        )

    data["surface_rule"]["sequence"] = seq
    NOISE_SETTINGS.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(" -> ".join(e["type"].split(":")[-1] for e in seq))
    return 0


if __name__ == "__main__":
    sys.exit(main())
