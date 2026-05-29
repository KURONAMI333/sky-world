# Sky World — Modrinth / CurseForge publish description

> First 1–2 lines are the card summary (SEO-critical).
> Categories: **worldgen** (primary) + **adventure** (secondary).
> Loaders: **neoforge**. Game versions: **1.21.1**. Side: **server-side** (datapack worldgen).
> **Requires Isekai API.**

---

**The overworld becomes a vertical sea of floating islands.** Aether-style continents scattered across a 150-block-tall band — explore up, down, and across a sky archipelago instead of solid ground. Powered by Isekai API.

## What it does

Sky World overlays the overworld's terrain with **scattered floating islands** distributed through a tall vertical band (active roughly Y 50–200), so the world reads as a true 3D archipelago — islands above you, below you, and off into the distance, with cloud layers threading between them. Every vanilla biome, ore, structure, and mob is remapped into the island volume by [Isekai API](https://modrinth.com/mod/isekai-api), so the world still feels like Minecraft — just airborne.

It also ships a **standalone Sky Realm dimension** (`/execute in sky_world:skyrealm`) — the same island generation as its own world you can travel to, leaving the overworld free for other mods if you prefer.

## Features

- **Vertical floating-island overworld** — continents across a wide Y band, not a thin shell. Curved island undersides, varied biomes, real depth.
- **Vanilla content preserved** — ores, structures, and mobs are remapped into the islands (no empty void worlds).
- **Ocean / cliff cleanup** — ocean monuments, shipwrecks, ocean ruins, and edge-leaking springs are excluded so islands stay clean.
- **Sky Realm dimension** — a separate dimension with the same island generation, for packs that want to keep a normal overworld.

## Requirements

| Mod | Required? |
|---|---|
| **Isekai API** | **Required** — Sky World is a datapack-style worldshape built entirely on Isekai's primitives |

## Compatibility

- **Coexists with** TerraBlender, YUNG's structure mods, map mods (Journeymap etc.), and dimension mods like Nullscape — tested in-game.
- **Mutually exclusive with** other overworld-overhaul mods (Terralith, William Wythers') — only one mod can own `overworld.json`. No crash; last-loaded wins. If you run Sky World alongside another overworld overhaul, use Sky World's **Sky Realm dimension** instead and let the other mod own the overworld.

## License & links

MIT. Source & issues: https://github.com/KURONAMI333/sky-world

Built on [Isekai API](https://modrinth.com/mod/isekai-api).
