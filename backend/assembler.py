import os
from jinja2 import Environment, FileSystemLoader
from typing import Dict
import zipfile
import io

# -------------------------------
# FIXED TEMPLATE PATH (IMPORTANT)
# -------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

print(f"[ASSEMBLER] TEMPLATE DIR: {TEMPLATE_DIR}")  # DEBUG

env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=True
)


# -------------------------------
# MAIN FUNCTION
# -------------------------------

def assemble_website(design_spec: Dict) -> str:
    design = design_spec["design"]

    template_name = design.get("template", "clean_modern") + ".html"

    print(f"[ASSEMBLER] Using template: {template_name}")

    try:
        template = env.get_template(template_name)
    except Exception as e:
        print(f"[ASSEMBLER] TEMPLATE LOAD ERROR: {str(e)}")
        raise Exception(f"Template not found: {template_name}")

    html = template.render(
        design=design
    )

    return html


# -------------------------------
# ZIP CREATOR (optional)
# -------------------------------

def create_zip(html: str, business_name: str) -> bytes:

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr("index.html", html)

    zip_buffer.seek(0)
    return zip_buffer.read()