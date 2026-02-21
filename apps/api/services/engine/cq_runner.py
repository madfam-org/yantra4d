import sys
import json
import logging

logger = logging.getLogger(__name__)

def run_cadquery_script(script_path, output_path, params_json, export_format):
    try:
        import cadquery as cq
    except ImportError:
        print("Error: CadQuery is not installed.")
        sys.exit(1)

    print(f"Loading parameters: {params_json}")
    params = json.loads(params_json)

    print(f"Executing CadQuery script: {script_path}")
    
    # Read the script
    with open(script_path, 'r') as f:
        script_content = f.text() if hasattr(f, 'text') else f.read()

    # Create an execution environment and inject parameters
    exec_globals = {"cq": cq}
    exec_globals.update(params)

    try:
        # Execute the script. The script should assign the final shape to an 'assembly', 'result', or 'part' variable.
        exec(script_content, exec_globals)
        
        # Find the result
        result = None
        for var_name in ['result', 'assembly', 'part', 'show_object']:
            if var_name in exec_globals and isinstance(exec_globals[var_name], (cq.Workplane, cq.Assembly, cq.Shape)):
                result = exec_globals[var_name]
                break
        
        if result is None:
            # Try to grab the last CadQuery object created
            for key, val in reversed(list(exec_globals.items())):
                if isinstance(val, (cq.Workplane, cq.Assembly, cq.Shape)):
                    result = val
                    break

        if result is None:
            print("Error: Could not find any CadQuery Workplane, Assembly, or Shape in the script to export.")
            sys.exit(1)

        print(f"Exporting to {export_format}: {output_path}")
        
        is_gltf_or_glb = export_format.upper() in ["GLTF", "GLB"]

        if is_gltf_or_glb:
            import tempfile
            import os
            try:
                import cascadio
            except ImportError:
                print("Error: cascadio library is missing. Cannot export high-quality GLB.")
                sys.exit(1)
            
            # Export to a temporary STEP file first
            with tempfile.NamedTemporaryFile(suffix=".step", delete=False) as tmp:
                temp_step_path = tmp.name
                
            try:
                if isinstance(result, cq.Assembly):
                    result.save(temp_step_path, "STEP")
                else:
                    cq.exporters.export(result, temp_step_path, "STEP")
                    
                print("Transcoding STEP to GLB via cascadio...")
                # cascadio creates a far superior, optimized binary GLB mesh
                cascadio.step_to_glb(temp_step_path, output_path)
            finally:
                if os.path.exists(temp_step_path):
                    os.remove(temp_step_path)
                    
        elif isinstance(result, cq.Assembly):
            result.save(output_path, export_format.upper())
        else:
            cq.exporters.export(result, output_path, export_format.upper())
            
        print("Rendering complete.")

    except Exception as e:
        print(f"Error executing CadQuery script: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python cq_runner.py <script_path> <output_path> <params_json> <export_format>")
        sys.exit(1)
        
    script_path = sys.argv[1]
    output_path = sys.argv[2]
    params_json = sys.argv[3]
    export_format = sys.argv[4]
    
    run_cadquery_script(script_path, output_path, params_json, export_format)
