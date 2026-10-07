"""Provider calls with content-addressed local cache and redacted failures."""
import math
import time
from urllib.parse import urlparse

from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError, InternalServerError
from common import ROOT, WORK, read, write, fingerprint


def settings():
    values = {}
    for line in (ROOT/'.env').read_text(encoding='utf-8-sig').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('\"').strip("'")
    base = values['LLM_BASE_URL']
    parsed = urlparse(base)
    if parsed.scheme != 'https' or parsed.hostname != 'dashscope.aliyuncs.com':
        raise ValueError('Only configured Beijing provider is permitted')
    return values


def client():
    cfg = settings()
    return OpenAI(base_url=cfg['LLM_BASE_URL'], api_key=cfg['LLM_API_KEY'], timeout=60, max_retries=0)


def validate(vector):
    if len(vector) != 1024 or not all(math.isfinite(x) for x in vector) or not any(vector):
        raise ValueError('Invalid embedding dimensions or values')


def embed(texts, model):
    profile = {'base_url': settings()['LLM_BASE_URL'], 'model': model, 'dimensions': 1024,
               'input_format': 'plain_title_path_body_v1', 'provider_weight_revision': 'not_exposed'}
    directory = WORK/'embeddings'/fingerprint(profile)
    vectors = [None]*len(texts)
    missing = {}
    for index, text in enumerate(texts):
        key = fingerprint({'profile': profile, 'text': text})
        path = directory/(key+'.json')
        if path.exists():
            value = read(path)
            if value['key'] != key:
                raise ValueError('Embedding cache key mismatch')
            validate(value['vector'])
            vectors[index] = value['vector']
        else:
            missing.setdefault(key, {'text': text, 'indices': []})['indices'].append(index)
    entries = list(missing.items())
    usage, seconds = [], []
    with client() as api:
        for offset in range(0, len(entries), 10):
            batch = entries[offset:offset+10]
            start = time.monotonic()
            for attempt in range(3):
                try:
                    response = api.embeddings.create(model=model, dimensions=1024,
                        input=[item['text'] for _,item in batch], encoding_format='float')
                    break
                except (RateLimitError, APITimeoutError, APIConnectionError, InternalServerError):
                    if attempt == 2:
                        raise
                    time.sleep(2**attempt)
            ordered = sorted(response.data, key=lambda x: x.index)
            if [r.index for r in ordered] != list(range(len(batch))):
                raise ValueError('Embedding response index mismatch')
            for (key, item), row in zip(batch, ordered):
                validate(row.embedding)
                write(directory/(key+'.json'), {'key': key, 'vector': row.embedding, 'profile': profile})
                for index in item['indices']:
                    vectors[index] = row.embedding
            usage.append(response.usage.model_dump())
            seconds.append(round(time.monotonic()-start, 3))
            print(f'{model}: embedded {min(offset+10,len(entries))}/{len(entries)} new inputs', flush=True)
    return vectors, {'profile': profile, 'cache_hits': len(texts)-sum(len(x['indices']) for x in missing.values()),
                     'new_unique_inputs': len(entries), 'actual_usage_this_run': usage, 'batch_seconds': seconds}
