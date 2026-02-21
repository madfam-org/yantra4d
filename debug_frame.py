import cadquery as cq

def cubic_bezier(p0, p1, p2, p3, steps=20):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
        y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts

w = 30
d = 20
rabbet_d = 10
rabbet_w = 5

p0 = (w/3, 0)
p1 = (w/2, d/4)
p2 = (w/2, d*0.75)
p3 = (w, d)

bez_pts = cubic_bezier(p0, p1, p2, p3, 20)[1:]
pts = [(0,0), p0] + bez_pts + [(w, d - rabbet_d), (w - rabbet_w, d - rabbet_d), (w - rabbet_w, 0)]

clean_pts = []
for p in pts:
    if not clean_pts or (abs(clean_pts[-1][0] - p[0]) > 1e-5 or abs(clean_pts[-1][1] - p[1]) > 1e-5):
        clean_pts.append(p)

print(f"Num pts: {len(clean_pts)}")
for p in clean_pts:
    print(f"({p[0]:.2f}, {p[1]:.2f})")

try:
    base = cq.Workplane("XY").polyline(clean_pts).close()
    print("Polyline closed successfully.")
    base.extrude(10)
    print("Extrude successful.")
except Exception as e:
    print(f"Exception: {e}")
