from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/verification/artifacts/phase8/review7'
OUT.mkdir(exist_ok=True)
for p in (ROOT/'tmp').glob('phase8-review7*'):
    if p.is_file():
        shutil.copy2(p,OUT/p.name)
    elif p.is_dir():
        for child in p.iterdir():
            if child.is_file(): shutil.copy2(child,OUT/child.name)
audit=json.loads((ROOT/'tmp/phase8-review7/audit.json').read_text(encoding='utf-8'))
current=[]
for row in audit['files']:
    data=(ROOT/row['path']).read_bytes()
    current.append({**row,'current_sha256':hashlib.sha256(data).hexdigest()})
changed=[r['path'] for r in current if r['current_sha256']!=r['sha256']]
root_audit=json.loads((ROOT/'docs/verification/artifacts/phase8/final-code-audit.json').read_text(encoding='utf-8'))
root_comparison=[]
for row in root_audit['records']:
    actual=hashlib.sha256((ROOT/row['file']).read_bytes()).hexdigest()
    if actual!=row['sha256']:root_comparison.append(row['file'])
result={'base':audit['base'],'files':len(current),'maximum_source_lines':audit['max_source_lines'],
    'source_changed_since_independent_audit':bool(changed),'changed':changed,
    'root_83_current_comparison_mismatches':root_comparison,
    'aggregate_sha256':hashlib.sha256('\n'.join(r['path']+' '+r['current_sha256'] for r in current).encode()).hexdigest(),
    'records':current,'security_matches':[r for r in audit['scan'] if r['category']!='any'],
    'frontend_any_matches':[r for r in audit['scan'] if r['category']=='any' and '/frontend/' in r['path']]}
(OUT/'current-source-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['ui-finish','ui-revoke','ui-neighbor']:
    text=(ROOT/f'tmp/phase8-review7-{name}.txt').read_text(encoding='utf-8-sig')
    value=text.split('### Result\n',1)[1].split('\n### Ran Playwright code',1)[0].strip()
    (OUT/(name+'.json')).write_text(json.dumps(json.loads(value),ensure_ascii=False,indent=2),encoding='utf-8')
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file()}
(OUT/'evidence-sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='records'},ensure_ascii=False))
print(json.dumps({r['path']:r['current_sha256'] for r in current if r['path'].endswith(('risk_records.py','attachment-api.ts','MessageTimeline.vue','0007_visual_evidence.py','graph.py','corrections.py'))},ensure_ascii=False))
