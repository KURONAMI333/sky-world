# Sky World

> Overworld becomes a sea of Aether II-style continental floating islands.
> Below the islands is the void. Vanilla ores, structures, and mobs are remapped onto the islands via Isekai API.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![NeoForge 1.21.1](https://img.shields.io/badge/NeoForge-1.21.1-orange.svg)](https://neoforged.net)
[![Depends on Isekai API](https://img.shields.io/badge/Depends-Isekai%20API-9333ea)](https://github.com/KURONAMI333/isekai-api)

---

## Concept

Every chunk of the overworld is rewritten as massive, thick floating islands separated by open void. Villages, ravines, strongholds, and ore veins all relocate into the island volume — you mine *through* the island instead of *down* to bedrock.

Pairs naturally with bridge mods (YUNG's Bridges), airship mods (Create: Aeronautics), and view-distance mods (Distant Horizons).

## How it works

Sky World is built on **[Isekai API](https://github.com/KURONAMI333/isekai-api)**, a neutral universal worldgen library.

The library provides composable density primitives (`mask_y_range`, `distance`, `step`, `mask`, ...) and rule-adaptation primitives (`SpatialPredicate`, `RemapStrategy`, ...). Sky World composes these primitives to express the floating-island worldshape — same primitives any third-party modder can use to express *their* worldshape.

The library has no idea Sky World exists; Sky World is just one application of the primitives.

## Status

**v0.1**: skeleton. `@Mod` entry + Isekai API facade smoke test. The actual `WorldshapeDescriptor` declaration and density function composition will land once Isekai API v0.2 ships the functional rule scanner and biome modifier generator.

## Dependencies

- NeoForge 1.21.1
- [Isekai API](https://github.com/KURONAMI333/isekai-api) (required)

## Building from source

```bash
./gradlew build
```

## License

[MIT License](LICENSE) — modpack inclusion welcome, no credit required.

## Credits

- Author: KURONAMI
