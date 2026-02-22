import os
import shutil
from pathlib import Path

projects_dir = Path("projects")
migrations = {
    "julia-vase": "julia-vase",
    "keyv2": "keyv2",
    "multiboard": "multiboard-parametric",
    "polydice": "polydice",
    "rugged-box": "rugged-box",
    "stemfie": "stemfie",
    "tablaco": "tablaco",
    "ultimate-box": "box-maker",
    "yapp-box": "yapp"
}

def migrate():
    for slug, subfolder in migrations.items():
        proj = projects_dir / slug
        vendor_dir = proj / "vendor"
        vendor_sub = vendor_dir / subfolder

        # Polydice explicitly vendors BOSL2 which is restricted to libs/
        # They should rely on the platform's global BOSL2 version.
        if slug == "polydice":
            bosl2_dir = vendor_sub / "BOSL2"
            if bosl2_dir.exists():
                shutil.rmtree(bosl2_dir)

        # Move the vendor files up to the native project root
        if vendor_sub.exists():
            # Delete .git inside the vendor subfolder before moving
            git_path = vendor_sub / ".git"
            if git_path.exists():
                if git_path.is_dir():
                    shutil.rmtree(git_path)
                else:
                    os.remove(git_path)
                    
            shutil.copytree(str(vendor_sub), str(proj), dirs_exist_ok=True)
            shutil.rmtree(vendor_dir)
            
        old_prefix = f"vendor/{subfolder}/"
        
        # Replace legacy path strings everywhere
        for file_path in proj.rglob("*"):
            if file_path.is_file() and file_path.suffix in [".scad", ".py", ".json", ".ts", ".md"]:
                try:
                    content = file_path.read_text(encoding="utf-8")
                    changed = False
                    
                    if old_prefix in content:
                        content = content.replace(old_prefix, "")
                        changed = True
                    
                    if slug == "polydice":
                        # Polydice uses local relative references to BOSL2 that are now globally resolved
                        if "<../BOSL2/" in content:
                            content = content.replace("<../BOSL2/", "<BOSL2/")
                            changed = True
                        if 'include <BOSL2/' in content:
                            content = content.replace('include <BOSL2/', 'include <BOSL2/')
                            changed = True
                            
                    if slug == "yapp-box":
                        # Yapp uses parent escape references which are illegal for secure cartridges
                        # OPENSCADPATH naturally injects root so they can be flattened
                        if "<../YAPPgenerator_v3.scad>" in content:
                            content = content.replace("<../YAPPgenerator_v3.scad>", "<YAPPgenerator_v3.scad>")
                            changed = True
                            
                    if changed:
                        file_path.write_text(content, encoding="utf-8")
                        
                except Exception:
                    pass

    print("Migration complete.")

if __name__ == "__main__":
    migrate()
