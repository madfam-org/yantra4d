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

ALLOWED_FILES = {
    "half_cube.scad": os.path.abspath(os.path.join(BASE_DIR, "../../half_cube.scad")),
    "tablaco.scad": os.path.abspath(os.path.join(BASE_DIR, "../../tablaco.scad"))
}

@app.route('/api/render', methods=['POST'])
def render_stl():
    data = request.json
    scad_filename = data.get('scad_file', 'half_cube.scad')
    
    if scad_filename not in ALLOWED_FILES:
        return jsonify({"status": "error", "error": f"Invalid SCAD file: {scad_filename}"}), 400
        
    scad_path = ALLOWED_FILES[scad_filename]
    
    # Construct OpenSCAD command
    cmd = [
        "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
        "-o", PREVIEW_STL,
    ]
    
    # Append all other parameters as -D flags
    for key, value in data.items():
        if key == 'scad_file':
            continue
            
        # Handle boolean conversion for OpenSCAD
        if isinstance(value, bool):
            val_str = str(value).lower()
        else:
            val_str = str(value)
            
        cmd.extend(["-D", f"{key}={val_str}"])
        
    cmd.append(scad_path)
    
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
