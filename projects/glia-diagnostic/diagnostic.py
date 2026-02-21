import cadquery as cq
import json
import argparse

def build_stethoscope(params):
    diaphragm_size_mm = float(params.get('diaphragm_size_mm', 44))
    
    outer_d = diaphragm_size_mm + 4.0
    
    # Main body
    head = cq.Workplane("XY").circle(outer_d / 2.0).extrude(20.0)
    
    # Hollow sound chamber (leaving 2mm at bottom)
    chamber = (
        cq.Workplane("XY", origin=(0, 0, 2.0))
        .circle(diaphragm_size_mm / 2.0)
        .extrude(18.1)
    )
    head = head.cut(chamber)
    
    # Tube connector (on +X side)
    # Origin of connector at X = outer_d/2, Y=0, Z=10
    connector = (
        cq.Workplane("YZ", origin=(outer_d / 2.0, 0, 10.0))
        .circle(8.0 / 2.0)
        .extrude(20.0)
    )
    
    # Air channel
    air_hole = (
        cq.Workplane("YZ", origin=(outer_d / 2.0 + 20.0, 0, 10.0))
        .circle(5.0 / 2.0)
        .extrude(-22.0)
    )
    
    head = head.union(connector).cut(air_hole)
    
    # Locking groove
    groove = (
        cq.Workplane("XY", origin=(0, 0, 18.0))
        .circle((diaphragm_size_mm + 4.1) / 2.0)
        .circle(diaphragm_size_mm / 2.0)
        .extrude(2.0)
    )
    head = head.cut(groove)
    
    return head.clean()

def build_otoscope(params):
    speculum_size_mm = float(params.get('speculum_size_mm', 4.0))
    
    height = 30.0
    base_d = 8.0
    tip_d = speculum_size_mm
    
    # Main cone
    specula = cq.Solid.makeCone(base_d / 2.0, tip_d / 2.0, height)
    
    # Hollow channel
    hollow = cq.Solid.makeCone(
        (base_d - 1.5) / 2.0, 
        (tip_d - 0.8) / 2.0, 
        height + 0.2
    ).translate((0, 0, -0.1))
    
    # Snap ring
    ring = (
        cq.Workplane("XY", origin=(0, 0, -0.5))
        .circle((base_d + 1.0) / 2.0)
        .extrude(2.0)
    )
    
    res = cq.Workplane("XY").add(specula).union(ring).cut(hollow)
    
    return res.clean()

def build(params, mode="stethoscope"):
    if mode == "otoscope":
        return build_otoscope(params)
    else:
        return build_stethoscope(params)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--mode", type=str, default="stethoscope")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params, mode=args.mode)
    
    if args.out:
        cq.exporters.export(res, args.out)
