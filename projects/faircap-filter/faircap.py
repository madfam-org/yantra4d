import cadquery as cq
import json
import argparse

def build(params):
    filter_type = params.get('filter_type', "charcoal")
    housing_od_mm = float(params.get('housing_od_mm', 40.0))
    housing_length_mm = float(params.get('housing_length_mm', 80.0))
    
    PCO_OD = 26.7
    
    # Main housing
    housing = cq.Workplane("XY").circle(housing_od_mm / 2.0).extrude(housing_length_mm)
    
    # Move origin to center of housing for easier math
    housing = housing.translate((0, 0, -housing_length_mm / 2.0))
    
    # Hollow interior
    hollow = (
        cq.Workplane("XY")
        .circle((housing_od_mm - 4.0) / 2.0)
        .extrude(housing_length_mm - 5.0)
        .translate((0, 0, - (housing_length_mm - 5.0) / 2.0))
    )
    
    # Top output hole
    top_hole = (
        cq.Workplane("XY")
        .circle(8.0 / 2.0)
        .extrude(10.0)
        .translate((0, 0, housing_length_mm / 2.0 - 5.0))
    )
    
    # Bottom PCO 1881 interface (Abstracted as a basic bore to represent female thread volume)
    # Thread logic omitted here to optimize headless execution speed.
    bottom_port = (
        cq.Workplane("XY")
        .circle(PCO_OD / 2.0)
        .extrude(15.0)
        .translate((0, 0, -housing_length_mm / 2.0 - 0.1))
    )
    
    res = housing.cut(hollow).cut(top_hole).cut(bottom_port)
    
    if filter_type == "mesh":
        # Simplified internal mesh partition
        mesh = (
            cq.Workplane("XY")
            .circle((housing_od_mm - 5.0) / 2.0)
            .extrude(2.0)
            .translate((0, 0, -housing_length_mm / 2.0 + 15.0))
        )
        
        # Add tiny holes to make it a "mesh"
        holes = (
            cq.Workplane("XY")
            .rarray(4, 4, int(housing_od_mm/4), int(housing_od_mm/4))
            .circle(1.0)
            .extrude(5.0)
            .translate((0, 0, -housing_length_mm / 2.0 + 13.0))
        )
        mesh = mesh.cut(holes)
        
        res = res.union(mesh)
        
    return res.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
