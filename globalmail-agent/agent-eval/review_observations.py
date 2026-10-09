"""Experimental lossless presentation codec; does not rewrite model evidence."""
import json
from globalmail_agent.knowledge.base import canonical


def parsed_observations(rows):
    result = [{**row, "content": json.loads(row["content"])} for row in rows]
    if original_observations(result) != rows:
        raise RuntimeError("observation_roundtrip_not_exact_no_HTTP")
    return result


def original_observations(rows):
    return [{**row, "content": canonical(row["content"]).decode()
        if isinstance(row["content"], dict) else row["content"]} for row in rows]
