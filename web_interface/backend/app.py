from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import os
import json

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCAD_FILE_PATH = os.path.abspath(os.path.join(BASE_DIR, "../../half_cube.scad"))
STATIC_FOLDER = os.path.join(BASE_DIR, "static")
PREVIEW_STL = os.path.join(STATIC_FOLDER, "preview.stl")
VERIFY_SCRIPT = os.path.abspath(os.path.join(BASE_DIR, "../../tests/verify_design.py"))

print(f"SCAD Path: {SCAD_FILE_PATH}")
print(f"Verify Script: {VERIFY_SCRIPT}")

os.makedirs(STATIC_FOLDER, exist_ok=True)

@app.route('/api/render', methods=['POST'])
def render_stl():
    data = request.json
    # Extract params with defaults
    size = data.get('size', 20.0)
    thick = data.get('thick', 2.5)
    show_base = str(data.get('show_base', True)).lower()
    show_walls = str(data.get('show_walls', True)).lower()
    show_mech = str(data.get('show_mech', True)).lower()
    
    # Construct OpenSCAD command
    # openscad -o output.stl -D var=val ... input.scad
    cmd = [
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        "-o", PREVIEW_STL,
        "-D", f"size={size}",
        "-D", f"thick={thick}",
        "-D", f"show_base={show_base}",
        "-D", f"show_walls={show_walls}",
        "-D", f"show_mech={show_mech}",
        SCAD_FILE_PATH
    ]
    
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return jsonify({
            "status": "success", 
            "stl_url": "http://localhost:5000/static/preview.stl",
            "log": result.stderr
        })
    except subprocess.CalledProcessError as e:
        return jsonify({"status": "error", "error": e.stderr}), 500

@app.route('/api/verify', methods=['POST'])
def verify_design():
    # Run verification on the PREVIEW stl
    if not os.path.exists(PREVIEW_STL):
        return jsonify({"status": "error", "message": "No preview generated yet"}), 400
        
    cmd = ["python3", VERIFY_SCRIPT, PREVIEW_STL]
    print(f"Verifying: {' '.join(cmd)}")
    
    try:
        # Run and capture stdout
        result = subprocess.run(cmd, capture_output=True, text=True)
        success = result.returncode == 0
        return jsonify({
            "status": "success" if success else "failure",
            "output": result.stdout + "\n" + result.stderr,
            "passed": success
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
