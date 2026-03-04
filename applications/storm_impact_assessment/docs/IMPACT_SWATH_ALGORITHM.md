# Asymmetric Intensity-Modulated Impact Swath & Coastal Impact Zones

> Algorithm reference for **Section 7.1b** of the Aurora hurricane-forecast notebook.
> Use this document as context when prompting for improvements or extensions.
>
> **v2** — January 2026: NHC radius fix, wind-extent buffer, right-of-track asymmetry, polygon smoothing.
> **v3** — February 2026: RSS uncertainty composition, symmetric morphological smoothing, exact end-cap sizing.

---

## Overview

The visualization produces a **single static matplotlib/Cartopy figure** with three layered systems:

| Layer | Purpose |
|-------|---------|
| **Part 1** — Asymmetric Swath | A 3-tier ribbon along the forecast track whose width = NHC track-uncertainty radius + pressure-derived wind-extent buffer, with right-of-track asymmetry (NH) |
| **Part 2** — Coastal Impact Zones | Track-wide coastline highlights (surge/flood warnings) computed for *every* forecast position, not just landfall |
| **Part 3** — Composed Figure | All layers rendered bottom-to-top on a Cartopy map with landfall detection, legends, and annotations |

---

## Prerequisites / Inputs

| Variable | Type | Source | Description |
|----------|------|--------|-------------|
| `track` | `pd.DataFrame` | `tracker.results()` from Aurora | Forecast track with columns `time`, `lat`, `lon` (0–360°), `msl` (Pa), `wind` (m/s) |
| `observed_track` | `pd.DataFrame` or `None` | HURDAT / IBTrACS / tropycal | Observed track with `time`, `lat`, `lon`, `vmax`, `mslp` |
| `selected_storm` | `SimpleStorm` | Notebook cell 8 | Storm metadata (`.name`, `.year`, etc.) |

A `lon_converted` column (`lon - 360` if `lon > 180`) is added to both DataFrames for PlateCarree plotting.

### MSLP resolution

Aurora's `msl` column is in **Pascals** and is divided by 100 to get **millibars (hPa)**. If `msl` is unavailable, the algorithm falls back to an `mslp` column (hPa), then to a neutral 1013 mb constant. Any remaining NaNs are filled with the column mean.

---

## Part 1 — Asymmetric Intensity-Modulated Impact Swath

### Step 1: Extract forecast positions

Each row of the track DataFrame is converted to a `track_points` list of dicts:

```python
{ lat, lon, lead_hours, mslp_mb, time }
```

`lead_hours` is computed as `(time - time[0]).total_seconds() / 3600`.

### Step 2: `km_to_degrees(km, lat)` helper

```
degrees = km / (111.0 × max(cos(radians(|lat|)), 0.01))
```

Converts a distance in km to approximate degrees of longitude at the given latitude. The `0.01` floor prevents division-by-zero near the poles.

### Step 3: NHC uncertainty radius as per-side offset

The NHC radii represent *how far the actual track center might deviate from the forecast* — i.e. a **per-side offset**, not a diameter. The base half-width at each forecast position is linearly interpolated from NHC's official table:

| Lead (h) | 0 | 6 | 12 | 24 | 36 | 48 | 72 | 96 | 120 |
|-----------|---|---|----|----|----|----|----|-----|-----|
| Radius (km) | 0 | 40 | 65 | 100 | 140 | 175 | 240 | 325 | 410 |

```python
base_half_km = max(nhc_radius_km(lead_hours), 40.0)   # minimum 40 km floor
```

> **v1 bug (fixed):** The original code divided the NHC radius by 2 (`w / 2`), treating it as a total width. This halved the swath relative to the NHC cone. The radius is already a half-width.

### Step 4: Pressure-derived wind-extent buffer

The NHC cone shows where the *center* might go. The actual hazard area extends further by the **radius of damaging winds**. Deeper pressure deficit → wider destructive wind field.

Empirical fit to Knaff et al. (2013) R34 / ROCI relationships:

```python
dp = max(1013.0 - mslp_mb, 0.0)
wind_extent_km = 40.0 + 2.0 × min(dp, 70.0)
```

| dp (mb) | wind_extent (km) | Approximate category |
|---------|-----------------|---------------------|
| 0 | 40 | Minimal / TD |
| 30 | 100 | Cat 1 |
| 50 | 140 | Cat 3 |
| 70 | 180 | Cat 4–5 (capped) |

The total **impact half-width** at each point uses **root-sum-of-squares (RSS)** composition:

```python
impact_half_km = sqrt(base_half_km² + wind_extent_km²)
```

> **v3 change:** The v2 code used **linear addition** (`base + wind_extent`), which assumes worst-case co-alignment of track error and wind radius — i.e. the center is displaced maximally AND the destructive winds extend fully in the same direction. In practice, track position uncertainty and wind-field radius are **independent error sources**. Standard uncertainty propagation (ISO GUM, Taylor 1997) prescribes RSS for independent terms. This better matches observed tropical-cyclone damage footprints (Powell & Reinhold 2007; Knaff et al. 2013).
>
> **Effect:** Reduces the outer-tier swath area by ~32 % compared to v2 while preserving the physical relationship between intensity and hazard extent.

### Step 5: Motion vectors & perpendicular offsets

For each position *i*, a **motion vector** `(dx, dy)` is computed:

- `i == 0`: forward difference → `(lon[1] - lon[0], lat[1] - lat[0])`
- `i == N-1`: backward difference → `(lon[i] - lon[i-1], lat[i] - lat[i-1])`
- otherwise: central difference → `(lon[i+1] - lon[i-1], lat[i+1] - lat[i-1])`

The unit vector is rotated ±90° to get the **left/right perpendicular**:

```python
mag = hypot(dx, dy)
(px, py) = (-dy/mag, dx/mag)      # left-hand perpendicular
```

The half-width in degrees: `half = km_to_degrees(impact_half_km, lat)`.

### Step 5b: Right-of-track asymmetry

Northern Hemisphere tropical cyclones have stronger winds on the **right side** (looking along the direction of motion) because the storm's translational velocity adds to the rotational winds there. Ref: Uhlhorn & Nolan (2012), Knaff et al. (2013).

```python
if lat >= 0:          # Northern Hemisphere
    right_factor = 1.25
    left_factor  = 0.80
else:                 # Southern Hemisphere — mirror
    right_factor = 0.80
    left_factor  = 1.25
```

Left and right offset points for each tier incorporate the asymmetry:

```python
left_off  = half × frac × left_factor
right_off = half × frac × right_factor
left[ti]  = (lon + px × left_off,  lat + py × left_off)
right[ti] = (lon - px × right_off, lat - py × right_off)
```

This makes the swath visibly wider on the right (east) side for northward-moving NH storms, matching observed damage patterns.

### Step 6: Build 3-tier swath polygons

Three nested Shapely `Polygon` rings are created from the left/right edge lists:

| Tier | Width fraction | Color | Alpha | Label |
|------|---------------|-------|-------|-------|
| Inner | 25 % | crimson | 0.55 | Inner core |
| Middle | 55 % | dark orange | 0.40 | Mid-level |
| Outer | 100 % | gold | 0.25 | Outer extent |

```python
ring = left[ti] + right[ti][::-1]
ring.append(ring[0])              # close the ring
polygon = ShapelyPolygon(ring).buffer(0)   # fix self-intersections
```

**Rounded end cap** (v2+): A circle is unioned at the last forecast position so the swath terminates with a smooth rounded shape instead of a flat cut. The cap radius equals the maximum left/right offset at the final point:

```python
r_end = max(dist(last_left, last_pt), dist(last_right, last_pt)) * 1.00
end_cap = Point(last_pt).buffer(r_end, resolution=64)
polygon = polygon.union(end_cap)
```

> **v3 change:** The end-cap multiplier was reduced from **1.05×** to **1.00×** (exact fit). The 5 % oversize in v2 added unnecessary area without improving visual smoothness.

**Morphological smoothing** (v2, refined in v3): After constructing each polygon, a symmetric dilate-then-erode pass removes jagged step artifacts from the discrete point offsets:

```python
polygon = polygon.buffer(0.12).buffer(-0.12)
```

> **v3 change:** The v2 smoothing used **asymmetric** dilation (`buffer(0.18).buffer(-0.10)`), which added net area (~0.08° equivalent dilation). The v3 smoothing is **zero-net** (`buffer(0.12).buffer(-0.12)`) — it closes jagged edges without inflating the polygon.

---

## Part 2 — Track-Wide Coastal Impact Zones

### Key concept

A storm doesn't need to make landfall to cause surge and flooding — passing nearby is enough. The algorithm highlights coastlines near the **entire track**, not just at landfall.

### Step 1: Define three impact tiers

| Tier | Base radius (km) | Color | Alpha | Physical meaning |
|------|------------------|-------|-------|-----------------|
| Core | 200 | crimson | 0.50 | Hurricane-force wind + severe surge |
| Surge | 450 | dark orange | 0.35 | Tropical storm winds / surge warning |
| Flood | 750 | light sky blue | 0.25 | Outer bands / rainfall flooding |

> The 200/450/750 km base radii are **empirical approximations** from Helene 2024's actual NHC warning footprint, not from a physical model.

### Step 2: Intensity scaling

All three radii are scaled by a factor based on the **pressure deficit** `dp = 1013 - MSLP`:

```python
scale = 1.0 + 0.4 × min(dp, 75) / 75
```

This gives a linear ramp from **1.0× at TD** up to **1.4× at strong Cat 4** (dp = 75 mb max).

### Step 3: Build tier polygons

For **every forecast position**, a Shapely circle is created at each tier's scaled radius:

```python
r_deg = km_to_degrees(base_km × scale, lat)
circle = Point(lon, lat).buffer(r_deg, resolution=48)
```

All circles per tier are merged via `unary_union()` into one combined polygon.

### Step 4: Coastline intersection

1. Load **Natural Earth 50 m land polygons**, clipped to an AOI bounding box (±12° around all track positions) for performance.
2. Intersect each tier polygon with `land_union.boundary` (the coastline geometry).
3. Buffer the resulting lines into fat drawable strips:
   - Core: 0.18°
   - Surge: 0.14°
   - Flood: 0.10°

The `shapely.prepared.prep()` optimization is used for the land polygon to speed up the `contains()` checks in landfall detection.

---

## Part 3 — Figure Composition

### Landfall detection

An **ocean→land transition** is detected when:

```python
not land_prep.contains(Point(lon[i-1], lat[i-1]))
and land_prep.contains(Point(lon[i], lat[i]))
```

Each landfall gets a **triangle marker** (`^`) plus an annotation box showing:
- Lead hours
- MSLP (mb)
- Estimated Vmax via Knaff-Zehr
- Saffir-Simpson category

### Knaff-Zehr wind estimation

Used for **labels and marker colors only**, not for swath widths:

```
dp = max(1013 - MSLP, 0)
Vmax (kt) = 6.3 × √dp + 0.15 × dp
```

### Saffir-Simpson category thresholds

| Category | Vmax (kt) | Color |
|----------|-----------|-------|
| Cat 5 | ≥ 137 | `#7030A0` (purple) |
| Cat 4 | ≥ 113 | `#C00000` (dark red) |
| Cat 3 | ≥ 96 | `#FF0000` (red) |
| Cat 2 | ≥ 83 | `#FFC000` (amber) |
| Cat 1 | ≥ 64 | `#FFFF00` (yellow) |
| TS | ≥ 34 | `#00B050` (green) |
| TD | < 34 | `#5B9BD5` (blue) |

### Layer order (bottom → top)

| Z-order | Layer |
|---------|-------|
| 0 | Base map (ocean, land fills) |
| 1 | Coastal impact tiers (flood → surge → core, outermost first) |
| 2 | Swath tiers (outer → mid → inner, outermost first) |
| 3 | Observed track (black solid line + dots) |
| 4 | Forecast track (blue dashed line) |
| 5 | Position markers (colored by SS category via Knaff-Zehr) |
| 6 | Start marker (lime star) |
| 7 | 24h time labels (+24h, +48h, …) and landfall triangle markers |
| 8 | Coastlines, borders, state lines (drawn on top) |
| 9 | Landfall annotation boxes |

### Map setup

- Projection: `PlateCarree`
- Coastlines: Natural Earth 50 m
- Features: land/ocean fill, state + country borders
- Extent: auto-calculated from `flood` tier bounds ∪ swath bounds ∪ observed track, plus 3° padding

### Legend

Two separate legends:
1. **Upper-left** — "Impact Tiers" (2 columns): 3 swath tiers + 3 coastal tiers
2. **Lower-left** — "Track Elements": observed track, forecast track, forecast start, landfall crossing

---

## Important Constraints

1. **Aurora's MSLP range is compressed** compared to reality. The wind-extent buffer uses **absolute** pressure deficit (dp = 1013 − MSLP) so it remains physically meaningful even with compressed ranges.

2. The **200/450/750 km** base radii for coastal impact zones are empirical approximations, not from a physical model.

3. **Knaff-Zehr** is used for labels/colors only, never for swath widths.

4. The algorithm is **generic** — it works for current (real-time) and historical storms of any basin, as long as the `track` DataFrame has `lat`, `lon`, `time`, and an MSLP column (`msl` in Pa or `mslp` in hPa). The right-of-track asymmetry automatically flips for Southern Hemisphere storms (lat < 0).

5. NaN handling: MSLP NaNs are filled with the column mean; if the entire column is NaN, a neutral 1013 mb fallback is used.

---

## Helper function signatures

```python
km_to_degrees(km: float, lat: float) -> float
nhc_radius_km(lead_hours: float) -> float
knaff_zehr(mslp_mb: float) -> float                            # Vmax in kt
ss_cat(vmax: float) -> str                                     # 'TD'..'Cat 5'
_add_geom(ax, geom, fc, alpha, zorder, ec='none', lw=0)        # render Shapely → mpl
```

> **Removed in v2:** `mslp_width_mult()` — replaced by the additive wind-extent buffer (Step 4).

---

## Possible improvements

_Use this section as a checklist for future prompt-driven iterations._

- [x] ~~Add **right-of-track bias**~~ — ✅ Implemented in v2 (1.25× right / 0.80× left in NH, mirrored in SH)
- [x] ~~Support **Southern Hemisphere** storms (flip right-of-track bias)~~ — ✅ Auto-flips when `lat < 0`
- [x] ~~**Normalize outer-tier area** without compromising accuracy~~ — ✅ Implemented in v3 (RSS composition, symmetric smoothing, exact end-cap); outer tier reduced ~32 %
- [ ] Use **actual wind radii** (34/50/64 kt) from NHC advisories when available instead of the empirical 200/450/750 km
- [ ] Animate the swath growth over time (frame per 6 h step)
- [ ] Incorporate **terrain elevation** to modulate inland flood zones
- [ ] Add **population density** overlay to estimate exposure
- [ ] Replace empirical coastal radii with **parametric wind model** (e.g., Holland 1980 or Willoughby 2006)
- [ ] Add **storm surge inundation** estimate using coastal DEM + storm tide
- [ ] Export the swath/coastal polygons as GeoJSON for downstream GIS workflows
