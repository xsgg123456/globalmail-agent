"""Make each probe result explicit, including startup, validation and cleanup failures."""
import json
from datetime import datetime, timezone


def write_report(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def run_reported(path, probe):
    started=datetime.now(timezone.utc).isoformat()
    write_report(path, {'status':'running','passed':False,'checks':[],'started_at':started})
    failed=False
    try:
        probe()
    except BaseException as exc:
        failed=True
        result=json.loads(path.read_text(encoding='utf-8'))
        result.update(passed=False,status='failed',error_type=type(exc).__name__)
        write_report(path,result)
    result=json.loads(path.read_text(encoding='utf-8'))
    if result.get('status')=='running':
        failed=True
        result.update(passed=False,error_type='MissingFinalReport')
    result.update(started_at=started,finished_at=datetime.now(timezone.utc).isoformat())
    result['status']='failed' if failed or result.get('passed') is False else 'completed'
    write_report(path,result)
    if result['status']=='failed':
        print(json.dumps({'probe':path.name,'passed':False,'error_type':result.get('error_type')}))
        raise SystemExit(1)


def cleanup_database(docker, container_id, nonce, env_file, result):
    """Try independent cleanup steps even when the daemon or container is unavailable."""
    errors=[]
    if container_id:
        try:
            label=docker('inspect',container_id,'--format','{{index .Config.Labels "globalmail.tech-spike"}}')
            if label!=nonce:
                raise RuntimeError('Temporary container ownership mismatch')
            docker('stop','--time','5',container_id)
            result['temporary_container_removed']=True
        except Exception as exc:
            result['temporary_container_removed']=False
            errors.append({'step':'container_cleanup','error_type':type(exc).__name__})
    try:
        env_file.unlink(missing_ok=True)
        result['temporary_credentials_removed']=True
    except Exception as exc:
        result['temporary_credentials_removed']=False
        errors.append({'step':'credential_cleanup','error_type':type(exc).__name__})
    if errors:
        result.update(passed=False,cleanup_errors=errors)
    return not errors
