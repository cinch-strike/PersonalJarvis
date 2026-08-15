# SG90 Servo — measured dimensions

Measured with digital calipers from the **actual servo** in this build
(TowerPro SG90, Jaycar `YM2758`). Clone dimensions vary by a millimetre or two,
so these supersede any datasheet figures — a pocket 1mm too small is a reprint.

All values in **mm**.

## Body

| Dimension | Value |
|---|---|
| Length | **22.61** |
| Width | **12.33** |
| Height (rectangular body only) | **22.31** |
| Height to top of blue boss | **26.69** |
| Height to top of white spline (total) | **29.50** |

Derived: boss rises **4.38** above the body; spline rises **2.81** above the boss.

## Mounting tabs

| Dimension | Value |
|---|---|
| Tab-to-tab overall length | **32.27** |
| **Screw-hole spacing (centre-to-centre)** | **28.00** ⭐ |
| Screw hole diameter | **2.0** (M2) |
| Tab thickness | **2.51** |
| **Tab height** (body bottom → tab underside) | **15.73** |
| Tab underside → spline tip | **13.77** |

The tab underside is the face that seats on a mounting plate, so tab height sets
how far the spline stands proud of that plate — which fixes the gap between the
cradle wall and the jaw.

Measured indirectly: bench → **top** of tab = 18.24, minus the 2.51 tab
thickness. The underside is tucked against the body and can't take a caliper jaw
flat; the top surface is exposed and easy. Both of the expected ranges checked
out (15–17 for tab height, 13–14 for underside→spline), and it leaves 6.58 of
body above the tab underside, which is right for an SG90.

⭐ The hole spacing is the one with no tolerance — get it wrong and the servo
won't bolt in.

## Output boss ("snowman" shape on top)

The boss is a large circle with a smaller protrusion beside it, not a plain
cylinder — the pocket needs to clear both.

| Dimension | Value |
|---|---|
| Big circle diameter (houses the spline) | **11.72** |
| Small protrusion diameter | **5.95** |
| Overall span (protrusion tip → far edge of circle) | **14.63** |
| Spline diameter (toothed shaft) | **4.79** |

Derived: the protrusion extends **2.91** beyond the big circle.

## Pivot position

| Dimension | Value |
|---|---|
| **Spline centre from nearest body end** | **5.86** |

The big circle's near edge is **flush with the end of the body**, so the spline
centre sits exactly one radius (5.86) in from that end.

**Why it matters:** the spline is the rotation axis. This locates the jaw hinge
relative to the servo pocket.

## Notes for the model

- Servo travel is **90°**, not 180° — the jaw's full swing must fit inside that.
- Jaw needs only ~20–30° of movement to read as talking.
- Include hard stops so the servo can't be driven past its limit and strip gears.
- Keep the jaw light: an SG90 is 1.6 kg·cm and a heavy jaw will stutter or buzz.
