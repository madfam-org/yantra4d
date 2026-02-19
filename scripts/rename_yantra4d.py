import os
import json
import glob
import re

print("Starting to rename and update yantra4d files...")

# Regex to safely replace just the scad file references
def replace_yantra4d(content):
    return re.sub(r'yantra4d_([a-zA-Z0-9_-]+\.scad)', r'\1', content)

# 1. Rename files
scad_files = glob.glob("projects/**/yantra4d_*.scad", recursive=True)
for file in scad_files:
    dir_name = os.path.dirname(file)
    base_name = os.path.basename(file)
    new_name = base_name.replace("yantra4d_", "")
    new_path = os.path.join(dir_name, new_name)
    os.rename(file, new_path)
    print(f"Renamed: {file} -> {new_path}")

# 2. Update references in all .scad files
all_scad = glob.glob("projects/**/*.scad", recursive=True)
for file in all_scad:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = replace_yantra4d(content)
    
    if content != new_content:
        with open(file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated internal scad dependencies in: {file}")

# 3. Update references in project.json and add attribution
all_json = glob.glob("projects/**/project.json", recursive=True)
for file in all_json:
    with open(file, 'r', encoding='utf-8') as f:
        content_str = f.read()

    new_content_str = replace_yantra4d(content_str)

    try:
        data = json.loads(new_content_str)
        is_hyperobject = False
        if "hyperobject" in data:
            is_hyperobject = True
        if "project" in data and "hyperobject" in data["project"] and data["project"]["hyperobject"].get("is_hyperobject"):
            is_hyperobject = True
        
        if is_hyperobject and "project" in data and "description" in data["project"]:
            desc = data["project"]["description"]
            en_attr = "Official Visualizer and Configurator: Yantra4D"
            es_attr = "Visualizador y configurador oficial: Yantra4D"
            
            if isinstance(desc, dict):
                modified = False
                if "en" in desc and "Yantra4D" not in desc["en"]:
                    desc["en"] = f"{desc['en']}\n\n{en_attr}"
                    modified = True
                if "es" in desc and "Yantra4D" not in desc["es"]:
                    desc["es"] = f"{desc['es']}\n\n{es_attr}"
                    if not modified:
                        modified = True
            elif isinstance(desc, str):
                if "Yantra4D" not in desc:
                    data["project"]["description"] = f"{desc}\n\n{en_attr}"

        final_content_str = json.dumps(data, indent=2) + "\n"
        with open(file, 'w', encoding='utf-8') as f:
            f.write(final_content_str)
        print(f"Updated manifest in: {file}")
            
    except Exception as e:
        print(f"Error processing {file}: {e}")

print("Done.")
