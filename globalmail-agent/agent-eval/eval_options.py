"""Frozen eval CLI and audited-history combinations; no service/model initialization."""
import argparse
from bootstrap import frozen_inputs


def options():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-freeze", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--group", choices=("closed-loop", "boundaries", "all"), default="all")
    parser.add_argument("--case", help="One frozen boundary ID; closed-loop begins from its supplied history")
    parser.add_argument("--seed-attempt", help="Accepted paid P7-01 used only as historical initialization")
    parser.add_argument("--prefix-attempt", help="Audited four paid P7-02 responses, then actual remaining HTTP")
    parser.add_argument("--prefix-engineering-only", action="store_true")
    parser.add_argument("--second-seed-attempt", help="Accepted paid P7-02 also reused only for history; fresh calls start at P7-03")
    parser.add_argument("--second-seed-engineering-only", action="store_true", help="Only replay accepted first two mails; zero new chat HTTP")
    parser.add_argument("--third-seed-attempt", help="Accepted paid P7-03 HITL also used as history; fresh calls start after human input")
    parser.add_argument("--third-seed-engineering-only", action="store_true", help="Only audit first three history stages; zero new chat HTTP")
    parser.add_argument("--semantic-gate", action="store_true", help="Wait for local complete-case semantic review before next paid run")
    parser.add_argument("--limit", type=int, default=9, help="Maximum real business runs; per-cycle budgets never increase")
    args = parser.parse_args()
    cases, frozen = frozen_inputs()
    seed = prefix = second = third = None
    if args.seed_attempt:
        if args.group == "boundaries":
            raise RuntimeError("history_seed_only_for_closed_loop")
        from history_seed import load_seed
        seed = load_seed(args.seed_attempt, cases["closed_loop"]["messages"][0])
    if args.prefix_attempt:
        if not seed or args.group != "closed-loop":
            raise RuntimeError("prefix_requires_authorized_closed_loop_seed")
        from prefix_replay import load_prefix
        prefix = load_prefix(args.prefix_attempt, cases["closed_loop"]["messages"][1])
    if args.prefix_engineering_only and (not prefix or args.limit != 1):
        raise RuntimeError("engineering_prefix_requires_single_second_mail")
    if args.second_seed_attempt:
        if not seed or prefix or args.group != "closed-loop":
            raise RuntimeError("second_history_seed_requires_first_seed_without_prefix_mode")
        from second_history_seed import load_second_seed
        second = load_second_seed(args.second_seed_attempt, cases["closed_loop"]["messages"][1])
    if args.second_seed_engineering_only and not second:
        raise RuntimeError("second_seed_engineering_requires_accepted_second_seed")
    if args.third_seed_attempt:
        if not second or prefix or args.second_seed_engineering_only:
            raise RuntimeError("third_history_seed_requires_accepted_first_two_seeds")
        from third_history_seed import load_third_seed
        third = load_third_seed(args.third_seed_attempt, cases["closed_loop"]["messages"][2])
    if args.third_seed_engineering_only and not third:
        raise RuntimeError("third_seed_engineering_requires_accepted_third_seed")
    return args, cases, frozen, seed, prefix, second, third
