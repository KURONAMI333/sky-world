"""Offline sampler for the Sky World final_density tree.

Faithful numpy port of vanilla 1.21.1 `ImprovedNoise` / `BlendedNoise` (the engine behind
`isekai_api:blended_noise`) plus the closed form of `isekai_api:band_density`, so island
shape can be measured without launching a client.

Ported from the decompiled 1.21.1 sources:
  net/minecraft/world/level/levelgen/synth/ImprovedNoise.java
  net/minecraft/world/level/levelgen/synth/BlendedNoise.java
  net/minecraft/world/level/levelgen/synth/PerlinNoise.java   (octave wiring, wrap)
  net/minecraft/world/level/levelgen/synth/SimplexNoise.java  (GRADIENT table)

Seed fidelity is deliberately NOT attempted: `BlendedNoise.createUnseeded` builds with
XoroshiroRandomSource(0) and the NoiseRouter re-seeds every octave from the world seed, so
no fixed seed reproduces a real world anyway. What is reproduced exactly is the *structure*
(octave frequencies, amplitudes, the y-smear, the min/max-limit blend), which is what
determines the statistics this script measures.

Usage:
    python tools/density_probe.py            # run the built-in report
"""

from __future__ import annotations

import numpy as np

# --- SimplexNoise.GRADIENT ------------------------------------------------------------
GRADIENT = np.array(
    [
        [1, 1, 0],
        [-1, 1, 0],
        [1, -1, 0],
        [-1, -1, 0],
        [1, 0, 1],
        [-1, 0, 1],
        [1, 0, -1],
        [-1, 0, -1],
        [0, 1, 1],
        [0, -1, 1],
        [0, 1, -1],
        [0, -1, -1],
        [1, 1, 0],
        [0, -1, 1],
        [-1, 1, 0],
        [0, -1, -1],
    ],
    dtype=np.float64,
)


def smoothstep(t):
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(t, a, b):
    return a + t * (b - a)


class ImprovedNoise:
    """One Perlin octave. Mirrors ImprovedNoise.noise(x, y, z, yScale, yMax)."""

    def __init__(self, rng: np.random.Generator):
        self.xo = rng.random() * 256.0
        self.yo = rng.random() * 256.0
        self.zo = rng.random() * 256.0
        self.p = rng.permutation(256).astype(np.int64)

    def _p(self, idx):
        return self.p[idx & 0xFF]

    def noise(self, x, y, z, y_scale, y_max):
        d0 = x + self.xo
        d1 = y + self.yo
        d2 = z + self.zo
        i = np.floor(d0)
        j = np.floor(d1)
        k = np.floor(d2)
        dx = d0 - i
        dy = d1 - j
        dz = d2 - k

        # y-smear: quantise the fractional y used for the gradient dot product
        if np.all(y_scale == 0.0):
            weird_dy = dy
        else:
            d7 = np.where((y_max >= 0.0) & (y_max < dy), y_max, dy)
            d6 = np.floor(d7 / y_scale + 1.0e-7) * y_scale
            weird_dy = dy - d6

        return self._sample_and_lerp(
            i.astype(np.int64),
            j.astype(np.int64),
            k.astype(np.int64),
            dx,
            weird_dy,
            dz,
            dy,
        )

    def _sample_and_lerp(self, gx, gy, gz, dx, wdy, dz, dy):
        i = self._p(gx)
        j = self._p(gx + 1)
        k = self._p(i + gy)
        l = self._p(i + gy + 1)
        i1 = self._p(j + gy)
        j1 = self._p(j + gy + 1)

        def grad_dot(idx, xf, yf, zf):
            g = GRADIENT[idx & 15]
            return g[..., 0] * xf + g[..., 1] * yf + g[..., 2] * zf

        d0 = grad_dot(self._p(k + gz), dx, wdy, dz)
        d1 = grad_dot(self._p(i1 + gz), dx - 1.0, wdy, dz)
        d2 = grad_dot(self._p(l + gz), dx, wdy - 1.0, dz)
        d3 = grad_dot(self._p(j1 + gz), dx - 1.0, wdy - 1.0, dz)
        d4 = grad_dot(self._p(k + gz + 1), dx, wdy, dz - 1.0)
        d5 = grad_dot(self._p(i1 + gz + 1), dx - 1.0, wdy, dz - 1.0)
        d6 = grad_dot(self._p(l + gz + 1), dx, wdy - 1.0, dz - 1.0)
        d7 = grad_dot(self._p(j1 + gz + 1), dx - 1.0, wdy - 1.0, dz - 1.0)

        sx = smoothstep(dx)
        sy = smoothstep(dy)
        sz = smoothstep(dz)
        lo = _lerp(sy, _lerp(sx, d0, d1), _lerp(sx, d2, d3))
        hi = _lerp(sy, _lerp(sx, d4, d5), _lerp(sx, d6, d7))
        return _lerp(sz, lo, hi)


class BlendedNoise:
    """vanilla minecraft:old_blended_noise.

    isekai_api:blended_noise is this with xz_scale = y_scale pinned to 0.25 and
    size_xz / size_y exposed as xz_factor / y_factor.
    """

    def __init__(
        self,
        size_xz: float,
        size_y: float,
        smear: float = 8.0,
        seed: int = 12345,
        xz_scale: float = 0.25,
        y_scale: float = 0.25,
    ):
        rng = np.random.default_rng(seed)
        # PerlinNoise.createLegacyForBlendedNoise: 16 / 16 / 8 independent octaves.
        # getOctaveNoise(j) indexes noiseLevels[len-1-j]; every octave is an independent
        # ImprovedNoise, so for statistics the mapping is a relabelling. Kept explicit.
        self.min_limit = [ImprovedNoise(rng) for _ in range(16)]
        self.max_limit = [ImprovedNoise(rng) for _ in range(16)]
        self.main = [ImprovedNoise(rng) for _ in range(8)]
        self.xz_mul = 684.412 * xz_scale
        self.y_mul = 684.412 * y_scale
        self.xz_factor = float(size_xz)
        self.y_factor = float(size_y)
        self.smear = float(smear)

    def compute(self, x, y, z):
        d0 = x * self.xz_mul
        d1 = y * self.y_mul
        d2 = z * self.xz_mul
        d3 = d0 / self.xz_factor
        d4 = d1 / self.y_factor
        d5 = d2 / self.xz_factor
        d6 = self.y_mul * self.smear
        d7 = d6 / self.y_factor

        d10 = np.zeros_like(np.asarray(d0, dtype=np.float64))
        f = 1.0
        for jj in range(8):
            d10 = d10 + self.main[jj].noise(d3 * f, d4 * f, d5 * f, d7 * f, d4 * f) / f
            f /= 2.0
        d16 = (d10 / 10.0 + 1.0) / 2.0

        d8 = np.zeros_like(d10)
        d9 = np.zeros_like(d10)
        f = 1.0
        for jj in range(16):
            d12 = d0 * f
            d13 = d1 * f
            d14 = d2 * f
            d15 = d6 * f
            d8 = d8 + self.min_limit[jj].noise(d12, d13, d14, d15, d1 * f) / f
            d9 = d9 + self.max_limit[jj].noise(d12, d13, d14, d15, d1 * f) / f
            f /= 2.0

        t = np.clip(d16, 0.0, 1.0)
        return (d8 / 512.0 + t * (d9 / 512.0 - d8 / 512.0)) / 128.0


# --- density function helpers ---------------------------------------------------------
def y_clamped_gradient(y, from_y, to_y, from_value, to_value):
    t = np.clip((y - from_y) / (to_y - from_y), 0.0, 1.0)
    return from_value + t * (to_value - from_value)


def band_density(
    y, noise_value, active_min_y, active_max_y, gradient_width, solidity_bias
):
    """Closed form of BandDensityDF.buildInner (invert=false).

    envelope = clamp01((y-(min-gw))/gw) * clamp01(((max+gw)-y)/gw)
    result   = -0.25 + envelope * (noise + 0.07 + bias)
    Inside the band (envelope=1) that is  noise + bias - 0.18.
    """
    env = y_clamped_gradient(
        y, active_min_y - gradient_width, active_min_y, 0.0, 1.0
    ) * y_clamped_gradient(y, active_max_y, active_max_y + gradient_width, 1.0, 0.0)
    return -0.25 + env * (noise_value + 0.07 + solidity_bias)


def squeeze(v):
    c = np.clip(v, -1.0, 1.0)
    return c / 2.0 - c * c * c / 24.0


# --- measurement ----------------------------------------------------------------------
def largest_component_extent(mask: np.ndarray, step: int):
    """4-connected component labelling on a boolean 2D slab. Returns (n, biggest_frac,
    biggest_bbox_blocks, occupancy)."""
    h, w = mask.shape
    labels = np.zeros((h, w), dtype=np.int32)
    cur = 0
    sizes = []
    boxes = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or labels[sy, sx]:
                continue
            cur += 1
            stack = [(sy, sx)]
            labels[sy, sx] = cur
            n = 0
            y0 = y1 = sy
            x0 = x1 = sx
            while stack:
                cy, cx = stack.pop()
                n += 1
                y0 = min(y0, cy)
                y1 = max(y1, cy)
                x0 = min(x0, cx)
                x1 = max(x1, cx)
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if (
                        0 <= ny < h
                        and 0 <= nx < w
                        and mask[ny, nx]
                        and not labels[ny, nx]
                    ):
                        labels[ny, nx] = cur
                        stack.append((ny, nx))
            sizes.append(n)
            boxes.append(max(y1 - y0, x1 - x0) * step)
    total = mask.sum()
    if not sizes:
        return 0, 0.0, 0, 0.0
    k = int(np.argmax(sizes))
    return len(sizes), sizes[k] / max(total, 1), boxes[k], total / mask.size


def autocorr_length(field: np.ndarray, step: int):
    """Horizontal lag (in blocks) at which the autocorrelation of a 2D slab first drops
    below 0.5."""
    f = field - field.mean()
    denom = (f * f).mean()
    for lag in range(1, field.shape[1] // 2):
        c = (f[:, :-lag] * f[:, lag:]).mean() / denom
        if c < 0.5:
            return lag * step
    return field.shape[1] // 2 * step
