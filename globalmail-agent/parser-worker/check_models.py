"""CLI installation check; prints only readiness, never personal paths or secrets."""
import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "globalmail-agent/backend/src"))
from globalmail_agent.knowledge.parser_profiles import model_home
from model_integrity import verify_models

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=("mineru_basic", "mineru_standard"), default="mineru_basic")
    args = parser.parse_args()
    os.environ["MINERU_HOME"] = str(model_home())
    try:
        verify_models(args.profile)
        print("PASS locked local parser models: " + args.profile)
    except ValueError as error:
        print(str(error))
        sys.exit(1)
