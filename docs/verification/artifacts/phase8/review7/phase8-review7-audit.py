from pathlib import Path
import hashlib
import json
import re
import subprocess
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'tmp/phase8-review7'
OUT.mkdir(exist_ok=True)
tracked = subprocess.check_output(['git','diff','--name-only','HEAD'], cwd=ROOT, text=True).splitlines()
untracked = subprocess.check_output(['git','ls-files','--others','--exclude-standard'], cwd=ROOT, text=True).splitlines()
files = sorted(set(p for p in tracked + untracked if p.startswith('globalmail-agent/') and Path(p).suffix in ('.py','.ts','.vue','.md') and '/src/types/import/' not in p))
records = []
scan = []
patterns = {'any':r'\bany\b','dangerous':r'\beval\s*\(|dangerouslySetInnerHTML|innerHTML|v-html',
    'secret':r'VITE_\w*(?:KEY|SECRET|TOKEN)|sk-ant-|sk-proj-|OPENAI_API_KEY\s*=|ANTHROPIC_API_KEY\s*=',
    'absolute_path':r'/Users/|C:\\Users\\|D:\\Work_Project\\'}
for name in files:
    path=ROOT/name
    raw=path.read_bytes(); source=raw.decode('utf-8')
    lines=source.splitlines()
    records.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'lines':len(lines)})
    for category,pattern in patterns.items():
        for number,line in enumerate(lines,1):
            if re.search(pattern,line): scan.append({'path':name,'line':number,'category':category,'text':line})
result={'base':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'files':records,'scan':scan,'max_source_lines':max((r['lines'] for r in records if '/src/' in r['path']),default=0)}
(OUT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
name='review7-label_'+'very-long-name_'*10+'photo.png'
image=Image.new('RGB',(800,500),'#edf3f7'); draw=ImageDraw.Draw(image)
draw.rectangle((80,80,720,420),fill='#4a82a6'); draw.rectangle((350,150,450,350),fill='#fbcc46')
draw.text((115,105),'REVIEW 7 actual controlled thumbnail',fill='white')
image.save(OUT/name)
print(json.dumps({'count':len(records),'max_source_lines':result['max_source_lines'],'scan':scan,'image':str(OUT/name)},ensure_ascii=False))
