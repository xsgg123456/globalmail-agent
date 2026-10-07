"""Rebuild the delivered business revision, without production/network access."""
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
TOOLS=Path(__file__).resolve().parent
for name in ['build_materials.py','build_scenarios.py','revise_business_materials.py','complete_step_fixtures.py','build_journeys.py']:
    subprocess.run([sys.executable,str(TOOLS/name)],cwd=ROOT,check=True)
target=ROOT/'tmp/pdfs/knowledge-v1';target.mkdir(parents=True,exist_ok=True)
subprocess.run(['pdftoppm','-r','90','-png',str(ROOT/'output/pdf/product-manuals-v1.pdf'),str(target/'page')],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(TOOLS/'validate_materials.py')],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(TOOLS/'validate_journeys.py')],cwd=ROOT,check=True)
subprocess.run([sys.executable,str(TOOLS/'test_journey_integrity.py')],cwd=ROOT,check=True)
