import os
import sys
import json
import logging
import math

logger = logging.getLogger(__name__)

# Restricted builtins for CadQuery script execution — blocks file I/O,
# network access, code generation, and import of dangerous modules.
_SAFE_BUILTINS = {
    # Core types and constructors
    "True": True, "False": False, "None": None,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set, "frozenset": frozenset,
    "bytes": bytes, "bytearray": bytearray, "complex": complex,
    # Iteration and ranges
    "range": range, "enumerate": enumerate, "zip": zip, "map": map, "filter": filter,
    "reversed": reversed, "sorted": sorted, "iter": iter, "next": next,
    # Math and numeric
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum, "pow": pow,
    "divmod": divmod,
    # Length and membership
    "len": len, "any": any, "all": all, "isinstance": isinstance, "issubclass": issubclass,
    "type": type, "id": id, "hash": hash,
    # String and repr
    "repr": repr, "format": format, "chr": chr, "ord": ord,
    "print": print,
    # Exceptions (scripts may catch/raise)
    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError,
    "RuntimeError": RuntimeError, "KeyError": KeyError, "IndexError": IndexError,
    "AttributeError": AttributeError, "StopIteration": StopIteration,
}

_BLOCKED_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "socket", "http", "urllib",
    "importlib", "ctypes", "signal", "multiprocessing", "threading",
    "pickle", "shelve", "code", "codeop", "compile", "compileall",
})


def _restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Import guard that blocks dangerous modules."""
    top = name.split(".")[0]
    if top in _BLOCKED_MODULES:
        raise ImportError(f"Import of '{name}' is not allowed in CadQuery scripts")
    return __builtins__["__import__"](name, globals, locals, fromlist, level) if isinstance(__builtins__, dict) \
        else __builtins__.__import__(name, globals, locals, fromlist, level)


def run_cadquery_script(script_path, output_path, params_json, export_format):
    try:
        import cadquery as cq
    except ImportError:
        print("Error: CadQuery is not installed.")
        sys.exit(1)

    print(f"Loading parameters: {params_json}")
    params = json.loads(params_json)

    # Validate script path is within the projects directory
    script_real = os.path.realpath(script_path)
    if not script_real.endswith(('.py', '.cq')):
        print(f"Error: Script must be a .py or .cq file, got: {script_path}")
        sys.exit(1)

    print(f"Executing CadQuery script: {script_path}")

    # Read the script
    with open(script_path, 'r') as f:
        script_content = f.read()

    # Create a sandboxed execution environment with restricted builtins
    safe_builtins = dict(_SAFE_BUILTINS)
    safe_builtins["__import__"] = _restricted_import

    exec_globals = {
        "__builtins__": safe_builtins,
        "cq": cq,
        "math": math,
        "__file__": script_path,
        "__name__": "__main__",
    }
    exec_globals.update(params)

    try:
        # Mock sys.argv so script's argparse doesn't break
        old_argv = sys.argv
        sys.argv = [script_path, "--params", params_json, "--out", output_path]

        # Execute the script. The script should assign the final shape to an 'assembly', 'result', or 'part' variable.
        exec(script_content, exec_globals)  # noqa: S102 — sandboxed via restricted builtins
        
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
    finally:
        sys.argv = old_argv

if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python cq_runner.py <script_path> <output_path> <params_json> <export_format>")
        sys.exit(1)
        
    script_path = sys.argv[1]
    output_path = sys.argv[2]
    params_json = sys.argv[3]
    export_format = sys.argv[4]
    
    run_cadquery_script(script_path, output_path, params_json, export_format)
