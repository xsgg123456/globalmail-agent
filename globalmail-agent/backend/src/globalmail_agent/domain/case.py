"""Case fact kinds describe evidence, never confer business authorization."""
from typing import Literal

FactKind = Literal["customer_report", "historical_claim", "visual_observation", "tool_fact",
                   "human_decision", "model_inference"]
