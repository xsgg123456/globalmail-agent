"""A content-free SDK4 OTLP trace for the observability retention smoke test."""
from pathlib import Path
import sys

from langfuse import Langfuse


def main() -> None:
    values = {}
    for line in Path(sys.argv[1]).read_text(encoding="utf-8-sig").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key] = value
    client = Langfuse(
        public_key=values["LANGFUSE_INIT_PROJECT_PUBLIC_KEY"],
        secret_key=values["LANGFUSE_INIT_PROJECT_SECRET_KEY"],
        base_url=f"http://127.0.0.1:{values['LANGFUSE_PORT']}",
        timeout=10,
    )
    with client.start_as_current_observation(
        as_type="span",
        name="observability-retention-smoke",
        trace_context={"trace_id": sys.argv[2]},
        metadata={"source": "infra-smoke", "customer_content": False},
    ):
        pass
    client.flush()
    client.shutdown()
    print("SDK4 content-free OTLP smoke exported; API readback is still required")


if __name__ == "__main__":
    main()
