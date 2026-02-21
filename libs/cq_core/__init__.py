import cadquery as cq
import math

# =============================================================================
# Yantra4D Core CadQuery Library
# Provides standardized CDG Interfaces and primitive math operations.
# =============================================================================

def create_thread(diameter, pitch, length):
    """
    Creates a standard metric straight thread profile.
    This replaces inline thread logic in bolts/nuts projects.
    """
    # Create a simple thread representation.
    # In a full B-Rep, this might be a complex helical sweep.
    # For many Yantra4D operations, simplified threads reduce STP file size unless needed.
    # We will implement a basic sweep.
    
    # Simple profile: Triangle
    profile = cq.Workplane("XZ").polyline([
        (0.0, -pitch/2.0),
        (diameter/2.0, 0.0),
        (0.0, pitch/2.0)
    ]).close().translate((diameter/2.0, 0, 0))
    
    # Helical sweep path
    path = cq.Wire.makeHelix(pitch=pitch, height=length, radius=diameter/2.0)
    thread = profile.sweep(path, isFrenet=True)
    
    return thread

def cdg_french_cleat(length=100, height=30, depth=15, angle=45):
    """
    Generates a standardized French Cleat negative profile.
    """
    rad = math.radians(angle)
    pts = [
        (0, 0),
        (depth, 0),
        (depth, height),
        (depth - (height * math.tan(rad)), height)
    ]
    
    profile = cq.Workplane("YZ").polyline(pts).close()
    
    cleat = profile.extrude(length)
    cleat = cleat.translate((-length/2, -height/2, 0))
    return cleat.clean()
