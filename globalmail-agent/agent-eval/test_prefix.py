"""No-network contract checks for replay isolation and the original time ceiling."""
import json
import unittest
from prefix_replay import PrefixReplay


class ProviderMustRemainUnused:
    model, configured = "test_only_no_network", True

    def request(self, *args, **kwargs):
        raise AssertionError("An invalid replay must not reach a provider")


class PrefixSafetyTests(unittest.TestCase):
    def test_changed_source_rejected_before_any_provider_call(self):
        prior = {"messages": [{"message_id": "old", "seq": 1, "sender": "customer", "body": "frozen input"}],
            "human_notes": []}
        fresh = {"messages": [{"message_id": "new", "seq": 1, "sender": "customer", "body": "different input"}],
            "human_notes": []}
        replay = PrefixReplay(ProviderMustRemainUnused(), (prior, [], [], {}))
        with self.assertRaisesRegex(RuntimeError, "prefix_visible_source_changed"):
            replay.request([{"role": "system", "content": "test"}, {"role": "user", "content": json.dumps(fresh)}])
        self.assertEqual(replay.new_http_calls, 0)

    def test_elapsed_original_time_cannot_be_reset_by_replay(self):
        from globalmail_agent.application.conversation_lock import ServiceError
        replay = PrefixReplay(ProviderMustRemainUnused(), ({}, [], [], {"origin_active_ms": 120000}))
        replay.index = 4
        with self.assertRaises(ServiceError) as failure:
            replay.request([])
        self.assertEqual(failure.exception.code, "budget_exhausted")
        self.assertEqual(replay.new_http_calls, 0)


if __name__ == "__main__":
    unittest.main()
