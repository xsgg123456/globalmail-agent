"""Validated danger bypasses another decision request, while respecting stop/input authority."""
from globalmail_agent.application.commit_outcome import commit_outcome


def risk_handoff(engine, store, context, job, understanding):
    proposal = {"kind": "handoff", "data": {"reason": "safety_risk",
        "summary": "客户报告危险迹象，已暂停自动处理：" + ", ".join(r["kind"] for r in understanding["risk_flags"]),
        "gaps": ["人工核查客户安全、对应商品与安全处置"], "draft": ""}}
    return commit_outcome(engine, store, context, job, understanding, proposal, safety=True)
