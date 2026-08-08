Turns the overworld into three bands of floating islands with open void between them, and moves vanilla's ores, structures and mobs into the island rock.

**Updating from 1.0.0 changes the world.** The island layout, the sky colour and the water are all different. Start a new world; an existing 1.0.0 save will generate mismatched terrain at the edge of what you have already explored.

## The three bands

- **Y 30–78** — large islands, widely spaced. Long crossings.
- **Y 116–176** — where you live. Denser, closer together, most of the land.
- **Y 212–242** — small and rare. Stepping stones near the cloud layer.

Between the bands is empty air, so the layers read as separate levels of the world rather than one thick slab.

## What moved

Ores follow each island's own top and bottom instead of absolute depth, so coal sits just under the grass of whatever island you are standing on and diamond sits near its underside. Structures and mobs are placed against the island volume the same way. Nothing generates at the old Y values, because there is nothing there.

There is no ocean. Water comes from ponds dug into the islands, roughly one attempt per twelve chunks, and surface lava lakes appear at vanilla's own rate. That is the whole water supply, so a pond is worth remembering where it is.

Clouds sit above the top band rather than cutting through it.

## Notes

Sky Realm, the separate dimension in 1.0.0, is gone. It had no way in — no portal was ever implemented — and its terrain was a copy of the overworld's.

Server-side world generation, with one client-side class that raises the cloud plane.

Requires [Isekai API](https://modrinth.com/mod/isekai-api) 2.1.0 or newer.

Free to use in any modpack, public or private.
