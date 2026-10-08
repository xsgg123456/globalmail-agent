"""Actual gateway/SDK child probe; does not use chat, vision, DB or business holdout."""
import hashlib
import json
import math
from pathlib import Path
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.embedding import EmbeddingGateway
from provider_config import configured_settings, write_json


def main():
    gateway = EmbeddingGateway(configured_settings())
    profile = gateway.profiles()[0]
    result = {'scope': 'developer_probe_not_model_accuracy', 'profile': profile}
    try:
        output = gateway.embed(profile, ['先断电，待灯泡冷却后检查固定环。', 'Disconnect power before checking the shade fitting.'])
        result.update(status='passed', dimensions=[len(v) for v in output['vectors']],
            unit_norms=[round(math.hypot(*v), 6) for v in output['vectors']],
            probe_sha256=hashlib.sha256(json.dumps(output['probe_vector']).encode()).hexdigest(),
            usage=output['usage'], seconds=round(output['seconds'], 3))
    except ServiceError as error:
        result.update(status='failed', code=error.code)
    write_json(Path(__file__).with_name('provider-results.json'), result)
    print(json.dumps(result, ensure_ascii=False))
    if result['status'] != 'passed': raise SystemExit(1)


if __name__ == '__main__': main()
