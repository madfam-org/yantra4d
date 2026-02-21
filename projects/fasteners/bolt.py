import cadquery as cq
import json
import argparse
import sys
import os

# Add monorepo root to sys.path to import centralized libs
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from libs.cq_core import create_thread

def build(params):
    diameter = float(params.get('diameter', 5.0))
    length = float(params.get('length', 20.0))
    head_diameter = float(params.get('head_diameter', 0.0))
    head_height = float(params.get('head_height', 0.0))
    head_style_id = int(params.get('head_style_id', 0))
    
    thread_enabled = params.get('thread_enabled', True)
    pitch = float(params.get('pitch', 0.8))
    
    head_d = head_diameter if head_diameter > 0 else diameter * 1.7
    head_h = head_height if head_height > 0 else diameter * 0.7
    
    # Shaft
    if thread_enabled:
        bolt = create_thread(diameter, pitch, length)
    else:
        bolt = cq.Workplane("XY").circle(diameter / 2.0).extrude(length)
    
    # Head
    head_wp = cq.Workplane("XY", origin=(0,0,length))
    
    if head_style_id == 0:
        # Hex head
        head = head_wp.polygon(6, head_d).extrude(head_h)
        bolt = bolt.union(head)
    elif head_style_id == 1:
        # Socket head
        head = head_wp.circle(head_d / 2.0).extrude(head_h)
        socket = head_wp.workplane(offset=head_h/2.0).polygon(6, diameter * 0.6).extrude(head_h/2.0 + 0.1)
        bolt = bolt.union(head).cut(socket)
    else:
        # Button head (approximated as a cylinder with rounded top or just a cylinder for now)
        # Using a fillet on the top edge to make it a dome
        head = head_wp.circle(head_d / 2.0).extrude(head_h * 0.6)
        # trying to fillet the top edge:
        bolt = bolt.union(head)
        try:
            bolt = bolt.edges(">Z").fillet((head_h * 0.6) - 0.1)
        except Exception:
            pass # fallback if fillet fails

    return bolt.clean()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--params", type=str, default="{}")
    parser.add_argument("--out", type=str, default="out.stl")
    args = parser.parse_args()
    
    params = json.loads(args.params)
    res = build(params)
    
    if args.out:
        cq.exporters.export(res, args.out)
