#!/usr/bin/env python3
"""RCON block-probe: 生成済みワールドの石バリアント・鉱石を実際に数える。

`mod-029-isekai-api/tools/probe_planet_ores.py` と同じ型（RCON + `/fill ... replace`
の "Successfully filled N block(s)" を counter に使う）。違いは対象が惑星球ではなく
XZ グリッド × Y スライスであることと、密度の分母を幾何計算ではなく「同じ窓で数えた
石系ブロックの合計」で取ること。空気だらけの浮島世界とバニラの地下を同じ物差しで
並べるには、体積ではなく岩体積で割る必要がある。

**破壊的**: 数えたブロックは air に置換される。使い捨てのワールドにだけ当てること。

Usage:
    python tools/probe_sky_ores.py --port 25597 --password skyprobe \
        --origin 512,512 --chunks 8 --bands 30:78,116:176,212:242 \
        --out probe_skyworld_postfix.json
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import struct
import sys
import time

FILLED_RE = re.compile(r"filled (\d+)")

# 既定の計数対象。gravel/sand は air fill で落下して未計測領域を汚すので入れない。
DEFAULT_BLOCKS = [
    "minecraft:stone",
    "minecraft:andesite",
    "minecraft:granite",
    "minecraft:diorite",
    "minecraft:tuff",
    "minecraft:deepslate",
    "minecraft:dirt",
    "minecraft:grass_block",
    "minecraft:coal_ore",
    "minecraft:iron_ore",
    "minecraft:copper_ore",
    "minecraft:deepslate_coal_ore",
    "minecraft:deepslate_iron_ore",
]

# 密度の分母（岩体積）に数えるもの
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


class Rcon:
    def __init__(self, host: str, port: int, password: str) -> None:
        self.sock = socket.create_connection((host, port), timeout=300)
        self.req_id = 0
        if self._send(3, password) is None:
            raise SystemExit("RCON auth failed")

    def _send(self, packet_type: int, body: str) -> str | None:
        self.req_id += 1
        sent_id = self.req_id
        payload = (
            struct.pack("<ii", sent_id, packet_type)
            + body.encode("utf-8")
            + b"\x00\x00"
        )
        self.sock.sendall(struct.pack("<i", len(payload)) + payload)
        length = struct.unpack("<i", self._recv_exact(4))[0]
        resp_id, _ = struct.unpack("<ii", self._recv_exact(8))
        text = self._recv_exact(length - 8)[:-2].decode("utf-8", "replace")
        if resp_id != sent_id:
            return None
        return text

    def _recv_exact(self, n: int) -> bytes:
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise SystemExit("RCON connection closed")
            buf += chunk
        return buf

    def cmd(self, command: str) -> str:
        return self._send(2, command) or ""

    def close(self) -> None:
        self.sock.close()


def fill_count(
    rcon: Rcon, x0: int, y0: int, z0: int, x1: int, y1: int, z1: int, block: str
) -> int:
    """その窓に `block` が何個あったかを返す（数えた分は air になる）。

    「0 個」と「コマンドが失敗した」を混同しないため、想定外の返答は例外にする。
    """
    reply = rcon.cmd(
        f"fill {x0} {y0} {z0} {x1} {y1} {z1} minecraft:air replace {block}"
    )
    m = FILLED_RE.search(reply)
    if m:
        return int(m.group(1))
    if "No blocks were filled" in reply or "no blocks" in reply.lower():
        return 0
    raise SystemExit(f"unexpected fill reply for {block} @({x0},{y0},{z0}): {reply!r}")


def wait_all_loaded(
    rcon: Rcon, cells: list[tuple[int, int]], y: int, timeout: float = 900.0
) -> None:
    """領域内の**全チャンク**の生成完了を待つ。

    中心1点だけを見ると、未生成チャンクの空気を「0 個」として数え、
    壊れた検査の沈黙が実測値として下流に流れる。
    """
    pending = list(cells)
    deadline = time.time() + timeout
    while pending and time.time() < deadline:
        still = []
        for cx, cz in pending:
            x, z = cx * 16 + 8, cz * 16 + 8
            if "The time is" not in rcon.cmd(
                f"execute if loaded {x} {y} {z} run time query gametime"
            ):
                still.append((cx, cz))
        pending = still
        if pending:
            time.sleep(3.0)
    if pending:
        raise SystemExit(
            f"{len(pending)} chunk(s) never finished generating: {pending[:5]}"
        )


def parse_bands(text: str) -> list[tuple[int, int]]:
    out = []
    for part in text.split(","):
        lo, hi = part.split(":")
        out.append((int(lo), int(hi)))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=25597)
    ap.add_argument("--password", default="skyprobe")
    ap.add_argument("--origin", default="512,512", help="領域の左下ブロック座標 x,z")
    ap.add_argument("--chunks", type=int, default=8, help="一辺のチャンク数")
    ap.add_argument(
        "--bands", default="30:78,116:176,212:242", help="計数する Y 帯（両端含む）"
    )
    ap.add_argument("--slice", type=int, default=16, help="Y スライスの高さ")
    ap.add_argument("--blocks", default=",".join(DEFAULT_BLOCKS))
    ap.add_argument("--out", default="probe_out.json")
    ap.add_argument("--label", default="")
    ap.add_argument(
        "--expect-rock",
        type=int,
        default=1,
        help="陽性対照。岩がこの数に満たなければ結果を捨てる。0 個という結果は、"
        "空の世界を測ったのか probe が壊れているのかを区別できないと意味がない",
    )
    args = ap.parse_args()

    ox, oz = (int(v) for v in args.origin.split(","))
    cx0, cz0 = ox // 16, oz // 16
    n = args.chunks
    bands = parse_bands(args.bands)
    blocks = [b for b in args.blocks.split(",") if b]
    cells = [(cx0 + i, cz0 + j) for i in range(n) for j in range(n)]

    rcon = Rcon(args.host, args.port, args.password)
    seed = rcon.cmd("seed")
    print(f"[{args.label}] {seed.strip()}")
    for g in (
        "randomTickSpeed 0",
        "doMobSpawning false",
        "doFireTick false",
        "doTileDrops false",
        "doEntityDrops false",
        "mobGriefing false",
    ):
        rcon.cmd(f"gamerule {g}")

    x0b, z0b = cx0 * 16, cz0 * 16
    x1b, z1b = x0b + n * 16 - 1, z0b + n * 16 - 1
    rcon.cmd(f"forceload add {x0b} {z0b} {x1b} {z1b}")
    probe_y = bands[0][0]
    wait_all_loaded(rcon, cells, probe_y)
    print(f"[{args.label}] {len(cells)} chunks generated, probing...")

    # Y スライス（下から上へ。上を先に air にすると落下ブロックが下を汚す）
    slices: list[tuple[int, int, int]] = []  # (band_index, y0, y1)
    for bi, (lo, hi) in enumerate(bands):
        y = lo
        while y <= hi:
            y1 = min(y + args.slice - 1, hi)
            slices.append((bi, y, y1))
            y = y1 + 1
    slices.sort(key=lambda s: s[1])

    data: dict = {
        "label": args.label,
        "origin": [x0b, z0b],
        "chunks": n,
        "bands": bands,
        "blocks": blocks,
        "cells": {},  # "cx,cz" -> {band_index: {block: count}}
    }
    t0 = time.time()
    ncmd = 0
    for ci, (ccx, ccz) in enumerate(cells):
        key = f"{ccx},{ccz}"
        per_band: dict[str, dict[str, int]] = {
            str(i): {b: 0 for b in blocks} for i in range(len(bands))
        }
        bx0, bz0 = ccx * 16, ccz * 16
        bx1, bz1 = bx0 + 15, bz0 + 15
        for bi, y0, y1 in slices:
            for b in blocks:
                per_band[str(bi)][b] += fill_count(rcon, bx0, y0, bz0, bx1, y1, bz1, b)
                ncmd += 1
        data["cells"][key] = per_band
        if (ci + 1) % 8 == 0:
            el = time.time() - t0
            print(
                f"  {ci+1}/{len(cells)} chunks  {ncmd} cmds  {el:.0f}s "
                f"({ncmd/max(el,0.001):.0f} cmd/s)",
                flush=True,
            )

    rcon.cmd(f"forceload remove {x0b} {z0b} {x1b} {z1b}")
    rcon.close()

    total_rock = sum(
        v
        for per_band in data["cells"].values()
        for band in per_band.values()
        for k, v in band.items()
        if k in STONE_FAMILY
    )
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    summarize(data)
    if total_rock < args.expect_rock:
        raise SystemExit(
            f"\n陽性対照が落ちた: 岩が {total_rock} 個しか無い (期待 >= {args.expect_rock})。"
            "\nこの窓の 0 は「鉱石が無い」の証拠にならない。ワールドが空か、"
            "領域がまだ生成されていないかを先に切り分けること。"
        )
    print(f"\nwrote {args.out}  ({ncmd} commands, {time.time()-t0:.0f}s)")
    return 0


def summarize(data: dict) -> None:
    bands = data["bands"]
    blocks = data["blocks"]
    print(f"\n=== {data['label']} ===")
    for bi, (lo, hi) in enumerate(bands):
        tot = {b: 0 for b in blocks}
        for per_band in data["cells"].values():
            for b in blocks:
                tot[b] += per_band[str(bi)][b]
        rock = sum(tot[b] for b in blocks if b in STONE_FAMILY)
        print(f"\nY {lo}..{hi}   岩体積(計数した石系合計) = {rock}")
        for b in blocks:
            if rock:
                print(f"  {b:<34}{tot[b]:>10}   {1e6*tot[b]/rock:>9.1f} /1M rock")
            else:
                print(f"  {b:<34}{tot[b]:>10}")


if __name__ == "__main__":
    sys.exit(main())
