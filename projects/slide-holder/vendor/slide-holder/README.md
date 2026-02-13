# Parametric Microscope Slide Holder

A parametric OpenSCAD model for 3D-printable microscope slide holders/racks.

![Microscope Slide Holder](https://img.shields.io/badge/OpenSCAD-Parametric-blue)

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `slides` | 10 | Number of slide slots |
| `thickness` | 1 mm | Slide thickness |
| `length` | 76.2 mm | Slide length (standard: 75–76.2 mm) |
| `width` | 25 mm | Slide width (standard: 25–26 mm) |

## Usage

Open `slide_holder.scad` in [OpenSCAD](https://openscad.org/) and adjust parameters in the Customizer panel, or override via CLI:

```bash
openscad -o slide_holder.stl \
  -D 'slides=10' \
  -D 'thickness=1' \
  -D 'length=76.2' \
  -D 'width=25' \
  slide_holder.scad
```

## Print Settings

- **Material**: PLA or PETG
- **Layer height**: 0.2 mm
- **Infill**: 20–30%
- **Supports**: Not required

## Attribution

Original design by **Lucas Wilder** — Michigan Technological University, EE 4777.

## License

MIT License — see [LICENSE](./LICENSE).
