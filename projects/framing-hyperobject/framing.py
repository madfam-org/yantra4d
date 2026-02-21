import cadquery as cq
import json
import argparse

def cubic_bezier(p0, p1, p2, p3, steps=20):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts

def build(params):
    width = float(params.get("width", 200))
    height = float(params.get("height", 250))
    depth = float(params.get("depth", 20))
    
    w = 30
    d = depth
    rabbet_d = 10
    rabbet_w = 5
    
    p0 = (w/3, 0)
    p1 = (w/2, d/4)
    p2 = (w/2, d*0.75)
    p3 = (w, d)
    
    bez_pts = cubic_bezier(p0, p1, p2, p3, 20)[1:] # Skip the first point since we'll draw to it
    pts = [(0,0), p0] + bez_pts + [(w, d - rabbet_d), (w - rabbet_w, d - rabbet_d), (w - rabbet_w, 0)]
    
    def make_side(L):
        # Draw on standard XY plane to avoid any mapping bugs, then rotate the Solid
        base = cq.Workplane("XY").polyline(pts).close()
        
        # Extrude along Z
        side = base.extrude((L/2) + w + 10, both=True)
        # Now the solid is extending along Z. The profile is on XY.
        # We want to map it so the length L is on the X axis.
        # Currently length is on Z. 
        # So we rotate around Y axis by 90 degrees.
        # Then Z becomes X, X becomes -Z, Y stays Y.
        
        # We need the profile's X (outward width) to map to Y, and Y (height) to map to Z.
        # Right now, profile X is X, profile Y is Y. 
        # If we rotate around X by 90: Y -> Z, Z -> -Y.
        # The extrusion was along Z. So it becomes -Y.
        # If we then rotate around Z by 90: X -> Y, Y -> -X.
        
        # Let's just create it on "YZ" but safely.
        # What if the duplicate point wasn't fully removed in my math? Let's clean the list just in case.
        clean_pts = []
        for p in pts:
            if not clean_pts or (abs(clean_pts[-1][0] - p[0]) > 1e-5 or abs(clean_pts[-1][1] - p[1]) > 1e-5):
                clean_pts.append(p)
                
        # Draw on YZ plane directly.
        yz_pts = [(p[0], p[1]) for p in clean_pts]
        side = cq.Workplane("YZ").polyline(yz_pts).close().extrude((L/2) + w + 10, both=True)
        
        # Cut miters using explicit 45-degree boolean subtractions
        # We want to keep X - Y <= L/2 (right side)
        cut_pts_1 = [(L/2, 0), (L/2 + 50, 0), (L/2 + 50, 50)]
        cut1 = cq.Workplane("XY").polyline(cut_pts_1).close().extrude(100, both=True)
        
        # We want to keep X + Y >= -L/2 (left side) -> Remove X + Y < -L/2
        cut_pts_2 = [(-L/2, 0), (-L/2 - 50, 0), (-L/2 - 50, 50)]
        cut2 = cq.Workplane("XY").polyline(cut_pts_2).close().extrude(100, both=True)
        
        side = side.cut(cut1).cut(cut2)
        
        return side

    top_edge = make_side(width).translate((0, height/2, 0))
    bottom_edge = make_side(width).rotate((0,0,0), (0,0,1), 180).translate((0, -height/2, 0))
    right_edge = make_side(height).rotate((0,0,0), (0,0,1), -90).translate((width/2, 0, 0))
    left_edge = make_side(height).rotate((0,0,0), (0,0,1), 90).translate((-width/2, 0, 0))
    
    frame = top_edge.union(bottom_edge).union(right_edge).union(left_edge)
    
    return frame

# Parse parameters injected by cq_runner or fall back to defaults
width_val = float(globals().get("width", 200))
height_val = float(globals().get("height", 250))
depth_val = float(globals().get("depth", 20))

result = build({
    "width": width_val,
    "height": height_val,
    "depth": depth_val
})

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    cq.exporters.export(res, args.out)

