import unittest
import io
from unittest.mock import patch

import action_engine
import atticus
from ai_provider_router import (
    AnthropicProvider, ClaudeSubscriptionProvider, FailureKind, GeminiProvider, HttpResponse, OpenAIChatGPTProvider, OpenAIProvider,
    ProviderId, ProviderPolicy, ProviderReply, ProviderRouter,
)


class MockTransport:
    def __init__(self, *responses): self.responses, self.calls = list(responses), []
    def post(self, url, headers, payload, timeout):
        self.calls.append((url, headers, payload, timeout))
        return self.responses.pop(0)


class ProviderRouterTests(unittest.TestCase):
    def test_claude_plan_status_is_sanitized_and_supported_modes_are_explicit(self):
        class Result:
            def __init__(self, stdout): self.stdout = stdout
        with patch.object(atticus.subprocess, 'run', return_value=Result('{"loggedIn":true,"authMethod":"claude.ai","subscriptionType":"team"}')):
            state = atticus.plan()
        self.assertEqual(state['authMode'], 'claude-subscription')
        self.assertTrue(state['ok'])
        self.assertNotIn('token', str(state).lower())
        with patch.object(atticus.subprocess, 'run', return_value=Result('{"loggedIn":true,"authMethod":"apiKey"}')):
            state = atticus.plan()
        self.assertFalse(state['ok'])
        self.assertEqual(state['authMode'], 'anthropic-api-key')

    def test_claude_plan_reports_an_unavailable_cli_without_exposing_state(self):
        with patch.object(atticus.subprocess, 'run', side_effect=FileNotFoundError):
            state = atticus.plan()
        self.assertEqual(state, {
            'ok': False, 'need': 'install', 'authMode': 'claude-subscription',
            'text': 'Claude Code is not installed.',
        })

    def test_provider_catalog_only_exposes_ready_providers_and_keeps_no_backup(self):
        catalog = atticus.provider_catalog([
            {'id': 'openai', 'state': 'unavailable'},
            {'id': 'claude-subscription', 'state': 'authenticated'},
        ])
        self.assertEqual(catalog, {'primary': [], 'backup': [{'value': 'none', 'label': 'No backup'}]})
        catalog = atticus.provider_catalog([{'id': 'openai', 'state': 'ready'}])
        self.assertEqual(catalog['primary'], [{'value': 'openai', 'label': 'ChatGPT plan'}])
        self.assertEqual(catalog['backup'], [{'value': 'none', 'label': 'No backup'}, {'value': 'openai', 'label': 'ChatGPT plan'}])

    def test_provider_state_does_not_claim_claude_ready_from_auth_metadata(self):
        with patch.object(atticus, 'plan', return_value={
            'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku',
            'text': 'Authenticated Claude Max account.',
        }), patch('openai_siwc.ChatGPTPlan.availability', return_value={
            'state': 'not_connected', 'models': [], 'modelsLoaded': False,
            'reasoningVerified': False, 'account': 'Not connected',
        }):
            state = atticus.api_provider_state()
        claude = next(row for row in state['providers'] if row['id'] == 'claude-subscription')
        self.assertEqual(claude['state'], 'authenticated')
        self.assertFalse(claude['reasoningVerified'])
        self.assertEqual(state['options']['primary'], [])

    def test_claude_subscription_policy_needs_explicit_free_only_approval(self):
        prefs = {'aiPrimary': 'claude-code', 'aiFreeOnly': True, 'aiFailover': True, 'aiClaudeSubscriptionNoCharge': True}
        with patch.object(atticus, 'pref', side_effect=lambda key, default: prefs.get(key, default)), \
             patch.object(atticus, 'plan', return_value={'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku'}):
            policy = atticus.api_provider_policy()
        self.assertEqual(policy.order, (ProviderId.CLAUDE_SUBSCRIPTION,))
        self.assertEqual(policy.no_charge_providers, frozenset({ProviderId.CLAUDE_SUBSCRIPTION}))

    def test_claude_subscription_is_separate_from_anthropic_api_key_mode(self):
        calls = []
        unavailable = ClaudeSubscriptionProvider(lambda: {'ok': False, 'need': 'api-key', 'authMode': 'anthropic-api-key', 'text': 'API key mode'}, lambda *_: calls.append(True), 'haiku')
        reply = unavailable.complete('hello', {}, 5)
        self.assertEqual(reply.provider, ProviderId.CLAUDE_SUBSCRIPTION)
        self.assertEqual(reply.failure.kind, FailureKind.AUTH)
        self.assertEqual(calls, [])

        supported = ClaudeSubscriptionProvider(lambda: {'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku'}, lambda prompt, model, timeout: ('Claude answer', True), 'haiku')
        reply = supported.complete('hello', {}, 5)
        self.assertTrue(reply.ok)
        self.assertEqual((reply.provider, reply.model), (ProviderId.CLAUDE_SUBSCRIPTION, 'haiku'))

    def test_claude_subscription_reports_pre_dispatch_quota_timeout_and_started_cancellation(self):
        quota = ClaudeSubscriptionProvider(
            lambda: {'ok': False, 'need': 'quota', 'authMode': 'claude-subscription', 'text': 'Claude subscription usage limit reached'},
            lambda *_: self.fail('quota state must not dispatch'), 'haiku')
        reply = quota.complete('hello', {}, 5)
        self.assertEqual(reply.failure.kind, FailureKind.QUOTA)
        self.assertTrue(reply.failure.retryable)

        timeout = ClaudeSubscriptionProvider(
            lambda: {'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku'},
            lambda *_: (_ for _ in ()).throw(TimeoutError()), 'haiku')
        reply = timeout.complete('hello', {}, 5)
        self.assertEqual(reply.failure.kind, FailureKind.TEMPORARY)
        self.assertTrue(reply.failure.retryable)

        cancelled = ClaudeSubscriptionProvider(
            lambda: {'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku'},
            lambda *_: ('Request cancelled after dispatch', False), 'haiku')
        reply = cancelled.complete('hello', {}, 5)
        self.assertEqual(reply.failure.kind, FailureKind.CANCELLED)
        self.assertFalse(reply.failure.retryable)

    def test_account_backed_failover_works_before_dispatch_in_both_directions(self):
        class TemporarilyUnavailablePlan:
            def complete(self, *_): raise RuntimeError('ChatGPT plan usage is temporarily unavailable.')
        claude = ClaudeSubscriptionProvider(lambda: {'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku'}, lambda *_: ('Claude backup', True), 'haiku')
        chatgpt = OpenAIChatGPTProvider(TemporarilyUnavailablePlan(), 'gpt-test')
        policy = ProviderPolicy((ProviderId.OPENAI, ProviderId.CLAUDE_SUBSCRIPTION), free_only=True,
                                no_charge_providers=frozenset({ProviderId.OPENAI, ProviderId.CLAUDE_SUBSCRIPTION}))
        reply = ProviderRouter({ProviderId.OPENAI: chatgpt, ProviderId.CLAUDE_SUBSCRIPTION: claude}, {}).complete('fact', policy)
        self.assertTrue(reply.ok); self.assertEqual(reply.attempts, (ProviderId.OPENAI, ProviderId.CLAUDE_SUBSCRIPTION))

        unavailable = ClaudeSubscriptionProvider(lambda: {'ok': False, 'need': 'install', 'authMode': 'claude-subscription', 'text': 'missing'}, lambda *_: self.fail('must not dispatch'), 'haiku')
        class ConnectedPlan:
            def complete(self, prompt, model, timeout): return 'ChatGPT backup', model
        chatgpt = OpenAIChatGPTProvider(ConnectedPlan(), 'gpt-test')
        policy = ProviderPolicy((ProviderId.CLAUDE_SUBSCRIPTION, ProviderId.OPENAI), free_only=True,
                                no_charge_providers=frozenset({ProviderId.CLAUDE_SUBSCRIPTION, ProviderId.OPENAI}))
        reply = ProviderRouter({ProviderId.CLAUDE_SUBSCRIPTION: unavailable, ProviderId.OPENAI: chatgpt}, {}).complete('fact', policy)
        self.assertTrue(reply.ok); self.assertEqual(reply.attempts, (ProviderId.CLAUDE_SUBSCRIPTION, ProviderId.OPENAI))

    def test_started_claude_request_is_never_retried_by_a_backup(self):
        backup_calls = []
        started = ClaudeSubscriptionProvider(lambda: {'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku'}, lambda *_: ('partial', False), 'haiku')
        class Backup:
            provider_id = ProviderId.OPENAI
            def complete(self, *_): backup_calls.append(True); return ProviderReply(ProviderId.OPENAI, model='gpt', text='must not run')
        reply = ProviderRouter({ProviderId.CLAUDE_SUBSCRIPTION: started, ProviderId.OPENAI: Backup()}, {}).complete(
            'fact', ProviderPolicy((ProviderId.CLAUDE_SUBSCRIPTION, ProviderId.OPENAI), free_only=False))
        self.assertEqual(reply.failure.kind, FailureKind.INVALID_RESPONSE)
        self.assertEqual(backup_calls, [])

    def test_claude_subscription_free_only_requires_explicit_approval_and_cancellation_dispatches_nothing(self):
        calls = []
        provider = ClaudeSubscriptionProvider(lambda: {'ok': True, 'authMode': 'claude-subscription', 'model': 'haiku'}, lambda *_: calls.append(True) or ('answer', True), 'haiku')
        router = ProviderRouter({ProviderId.CLAUDE_SUBSCRIPTION: provider}, {})
        blocked = router.complete('fact', ProviderPolicy((ProviderId.CLAUDE_SUBSCRIPTION,), free_only=True))
        self.assertEqual(blocked.failure.kind, FailureKind.POLICY); self.assertEqual(calls, [])
        cancelled = router.complete('fact', ProviderPolicy((ProviderId.CLAUDE_SUBSCRIPTION,), free_only=False), cancelled=lambda: True)
        self.assertEqual(cancelled.failure.kind, FailureKind.CANCELLED); self.assertEqual(calls, [])

    def test_free_only_skips_unapproved_provider_without_contacting_it(self):
        transport = MockTransport(HttpResponse(200, '{"output_text":"should not be used"}'))
        router = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(transport, "test")}, {"OPENAI_API_KEY": "test-key"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.OPENAI,), free_only=True))
        self.assertEqual(reply.failure.kind, FailureKind.POLICY)
        self.assertEqual(transport.calls, [])

    def test_free_only_allows_an_explicitly_approved_no_charge_route(self):
        transport = MockTransport(HttpResponse(200, '{"candidates":[{"content":{"parts":[{"text":"Free answer"}]}}]}'))
        router = ProviderRouter({ProviderId.GEMINI: GeminiProvider(transport, "gemini-free-model")}, {"GEMINI_API_KEY": "test-key"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.GEMINI,), free_only=True, no_charge_providers=frozenset({ProviderId.GEMINI})))
        self.assertTrue(reply.ok)
        self.assertEqual(reply.provider, ProviderId.GEMINI)
        self.assertEqual(reply.model, "gemini-free-model")
        self.assertEqual(len(transport.calls), 1)

    def test_free_only_moves_past_an_unapproved_primary_to_an_approved_backup(self):
        primary = MockTransport(HttpResponse(200, '{"output_text":"must not be called"}'))
        backup = MockTransport(HttpResponse(200, '{"candidates":[{"content":{"parts":[{"text":"Backup answer"}]}}]}'))
        router = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(primary, "paid-model"), ProviderId.GEMINI: GeminiProvider(backup, "free-model")}, {"OPENAI_API_KEY": "o", "GEMINI_API_KEY": "g"})
        policy = ProviderPolicy((ProviderId.OPENAI, ProviderId.GEMINI), free_only=True, no_charge_providers=frozenset({ProviderId.GEMINI}))
        reply = router.complete("hello", policy)
        self.assertTrue(reply.ok)
        self.assertEqual(reply.attempts, (ProviderId.GEMINI,))
        self.assertEqual(primary.calls, [])
        self.assertEqual(len(backup.calls), 1)

    def test_disabled_failover_never_uses_another_provider(self):
        primary = MockTransport(HttpResponse(200, '{"output_text":"must not be called"}'))
        backup = MockTransport(HttpResponse(200, '{"candidates":[{"content":{"parts":[{"text":"must not be called"}]}}]}'))
        router = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(primary, "paid-model"), ProviderId.GEMINI: GeminiProvider(backup, "free-model")}, {"OPENAI_API_KEY": "o", "GEMINI_API_KEY": "g"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.OPENAI, ProviderId.GEMINI), failover=False, free_only=True, no_charge_providers=frozenset({ProviderId.GEMINI})))
        self.assertEqual(reply.failure.kind, FailureKind.POLICY)
        self.assertEqual(primary.calls, [])
        self.assertEqual(backup.calls, [])

    def test_unavailable_adapter_is_skipped_for_a_configured_backup(self):
        backup = MockTransport(HttpResponse(200, '{"output_text":"Recovered"}'))
        router = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(backup, "backup-model")}, {"OPENAI_API_KEY": "o"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.GEMINI, ProviderId.OPENAI), free_only=False))
        self.assertTrue(reply.ok)
        self.assertEqual(reply.attempts, (ProviderId.GEMINI, ProviderId.OPENAI))
        self.assertEqual(len(backup.calls), 1)

    def test_retryable_primary_failure_fails_over_once(self):
        first, second = MockTransport(HttpResponse(429, '{"error":"rate limit"}')), MockTransport(HttpResponse(200, '{"output_text":"Safe answer"}'))
        router = ProviderRouter({ProviderId.ANTHROPIC: AnthropicProvider(first, "test"), ProviderId.OPENAI: OpenAIProvider(second, "test")}, {"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "o"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.ANTHROPIC, ProviderId.OPENAI), free_only=False))
        self.assertTrue(reply.ok)
        self.assertEqual(reply.attempts, (ProviderId.ANTHROPIC, ProviderId.OPENAI))
        self.assertEqual(reply.model, "test")
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(len(second.calls), 1)

    def test_auth_failure_fails_over_once_without_exposing_credential(self):
        first, second = MockTransport(HttpResponse(401, '{"error":"bad key"}')), MockTransport(HttpResponse(200, '{"output_text":"unused"}'))
        router = ProviderRouter({ProviderId.ANTHROPIC: AnthropicProvider(first, "test"), ProviderId.OPENAI: OpenAIProvider(second, "test")}, {"ANTHROPIC_API_KEY": "private", "OPENAI_API_KEY": "backup"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.ANTHROPIC, ProviderId.OPENAI), free_only=False))
        self.assertTrue(reply.ok)
        self.assertEqual(reply.attempts, (ProviderId.ANTHROPIC, ProviderId.OPENAI))
        self.assertEqual(len(second.calls), 1)
        self.assertNotIn("private", str(reply))

    def test_each_provider_uses_documented_header_shape_and_text_only_result(self):
        anthropic = MockTransport(HttpResponse(200, '{"content":[{"type":"text","text":"A"}]}'))
        openai = MockTransport(HttpResponse(200, '{"output_text":"O"}'))
        gemini = MockTransport(HttpResponse(200, '{"candidates":[{"content":{"parts":[{"text":"G"}]}}]}'))
        providers = {ProviderId.ANTHROPIC: AnthropicProvider(anthropic, "test"), ProviderId.OPENAI: OpenAIProvider(openai, "test"), ProviderId.GEMINI: GeminiProvider(gemini, "test")}
        env = {"ANTHROPIC_API_KEY": "a", "OPENAI_API_KEY": "o", "GEMINI_API_KEY": "g"}
        for provider_id, expected in ((ProviderId.ANTHROPIC, "A"), (ProviderId.OPENAI, "O"), (ProviderId.GEMINI, "G")):
            reply = ProviderRouter(providers, env).complete("hello", ProviderPolicy((provider_id,), free_only=False))
            self.assertEqual(reply.text, expected)
            self.assertFalse(hasattr(reply, "actions"))
        self.assertIn("x-api-key", anthropic.calls[0][1])
        self.assertIn("Authorization", openai.calls[0][1])
        self.assertIn("x-goog-api-key", gemini.calls[0][1])

    def test_missing_credentials_and_duplicate_priority_are_rejected(self):
        router = ProviderRouter({ProviderId.GEMINI: GeminiProvider(MockTransport(), "test")}, {})
        reply = router.complete("hello", ProviderPolicy((ProviderId.GEMINI,), free_only=False))
        self.assertEqual(reply.failure.kind, FailureKind.AUTH)
        invalid = router.complete("hello", ProviderPolicy((ProviderId.GEMINI, ProviderId.GEMINI), free_only=False))
        self.assertEqual(invalid.failure.kind, FailureKind.UNSUPPORTED)

    def test_model_must_be_explicit_to_avoid_claiming_a_provider_default(self):
        router = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(MockTransport())}, {"OPENAI_API_KEY": "key"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.OPENAI,), free_only=False))
        self.assertEqual(reply.failure.kind, FailureKind.UNSUPPORTED)

    def test_invalid_model_and_temporary_transport_failure_are_safe_and_bounded(self):
        invalid = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(MockTransport(), "../not-a-model")}, {"OPENAI_API_KEY": "key"})
        self.assertEqual(invalid.complete("hello", ProviderPolicy((ProviderId.OPENAI,), free_only=False)).failure.kind, FailureKind.UNSUPPORTED)

        class TimeoutTransport:
            def __init__(self): self.calls = 0
            def post(self, *_): self.calls += 1; raise TimeoutError()
        timed_out, backup = TimeoutTransport(), MockTransport(HttpResponse(200, '{"candidates":[{"content":{"parts":[{"text":"Recovered"}]}}]}'))
        router = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(timed_out, "test"), ProviderId.GEMINI: GeminiProvider(backup, "test")}, {"OPENAI_API_KEY": "o", "GEMINI_API_KEY": "g"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.OPENAI, ProviderId.GEMINI), free_only=False))
        self.assertTrue(reply.ok)
        self.assertEqual(timed_out.calls, 1)
        self.assertEqual(len(backup.calls), 1)

    def test_cancellation_stops_before_a_provider_request_or_failover(self):
        transport = MockTransport(HttpResponse(200, '{"output_text":"must not be used"}'))
        router = ProviderRouter({ProviderId.OPENAI: OpenAIProvider(transport, "test")}, {"OPENAI_API_KEY": "key"})
        reply = router.complete("hello", ProviderPolicy((ProviderId.OPENAI,), free_only=False), cancelled=lambda: True)
        self.assertEqual(reply.failure.kind, FailureKind.CANCELLED)
        self.assertEqual(transport.calls, [])

    def test_app_provider_state_exposes_only_account_backed_routes(self):
        prefs = {'aiPrimary': 'openai', 'aiFreeOnly': True, 'aiFailover': True, 'aiOpenAIModel': 'test-model'}
        with patch.object(atticus, 'pref', side_effect=lambda key, default: prefs.get(key, default)):
            state = atticus.api_provider_state({'OPENAI_API_KEY': 'must-not-appear'})
        self.assertEqual(state['primary'], 'openai')
        self.assertTrue(state['freeOnly'])
        self.assertIn('ChatGPT plan:', str(state))
        self.assertNotIn('must-not-appear', str(state))
        self.assertEqual({p['id'] for p in state['providers']}, {'openai', 'claude-subscription'})
        self.assertNotIn('api-key', str(state))

    def test_unresolved_api_selected_request_does_not_start_claude_or_an_action(self):
        prefs = {'aiPrimary': 'openai', 'aiFreeOnly': True, 'aiFailover': True}
        reply = ProviderReply(ProviderId.OPENAI, failure=atticus.ProviderFailure(FailureKind.POLICY, 'Free-only blocked this request.'))
        with patch('sys.argv', ['atticus.py', '--wait']), patch('sys.stdin', io.StringIO('Desktop\tWhat is a nebula?\n')), \
             patch.object(atticus, 'pref', side_effect=lambda key, default: prefs.get(key, default)), \
             patch.object(atticus, 'ping'), patch.object(atticus, 'fast', return_value=None), \
             patch.object(atticus, 'wait_commit', return_value=True), patch.object(atticus, 'run_api_provider', return_value=reply), \
             patch.object(atticus, 'remember_turn'), patch.object(atticus, 'log_turn') as logged, \
             patch.object(atticus, 'say') as say, patch.object(atticus, 'start_claude', side_effect=AssertionError('Claude must not start')), \
             patch.object(atticus.signal, 'signal'):
            atticus.main()
        say.assert_called_once_with('!', 'Free-only blocked this request.')
        self.assertEqual(logged.call_args.kwargs['provider'], 'openai')

    def test_removed_api_backup_selection_is_ignored_before_routing(self):
        prefs = {'aiPrimary': 'openai', 'aiBackup1': 'anthropic', 'aiBackup2': 'gemini', 'aiFreeOnly': True}
        with patch.object(atticus, 'pref', side_effect=lambda key, default: prefs.get(key, default)):
            policy = atticus.api_provider_policy()
        self.assertEqual(policy.order, (ProviderId.OPENAI,))
        self.assertEqual(policy.no_charge_providers, frozenset())

    def test_configured_api_backup_can_answer_when_claude_code_is_unavailable(self):
        prefs = {'aiPrimary': 'claude-code', 'aiBackup1': 'gemini', 'aiFreeOnly': True, 'aiGeminiNoCharge': True, 'aiFailover': True}
        reply = ProviderReply(ProviderId.GEMINI, model='gemini-free-model', text='A nebula is a cloud of gas and dust.')
        with patch('sys.argv', ['atticus.py', '--wait']), patch('sys.stdin', io.StringIO('Desktop\tWhat is a nebula?\n')), \
             patch.object(atticus, 'pref', side_effect=lambda key, default: prefs.get(key, default)), \
             patch.object(atticus, 'ping'), patch.object(atticus, 'route_action', return_value=(action_engine.Route(False), None)), \
             patch.object(atticus, 'fast', return_value=None), patch.object(atticus, 'licensed', return_value=False), \
             patch.object(atticus, 'wait_commit', return_value=True), patch.object(atticus, 'run_api_provider', return_value=reply) as run_api, \
             patch.object(atticus, 'remember_turn'), patch.object(atticus, 'log_turn') as logged, \
             patch.object(atticus, 'start_claude', side_effect=AssertionError('Claude must not start')), \
             patch.object(atticus, 'say') as say, patch.object(atticus.signal, 'signal'):
            atticus.main()
        run_api.assert_called_once_with('What is a nebula?')
        say.assert_called_once_with('✓', 'A nebula is a cloud of gas and dust.\nAnswered by gemini (gemini-free-model).')
        self.assertEqual(logged.call_args.kwargs['provider'], 'gemini (gemini-free-model)')

    def test_configured_api_backup_can_answer_when_claude_cli_is_missing(self):
        prefs = {'aiPrimary': 'claude-code', 'aiBackup1': 'openai', 'aiFreeOnly': False, 'aiFailover': True}
        reply = ProviderReply(ProviderId.OPENAI, model='backup-model', text='A concise answer.')
        with patch('sys.argv', ['atticus.py', '--wait']), patch('sys.stdin', io.StringIO('Desktop\tExplain a quasar\n')), \
             patch.object(atticus, 'pref', side_effect=lambda key, default: prefs.get(key, default)), \
             patch.object(atticus, 'ping'), patch.object(atticus, 'route_action', return_value=(action_engine.Route(False), None)), \
             patch.object(atticus, 'fast', return_value=None), patch.object(atticus, 'licensed', return_value=True), \
             patch.object(atticus, 'start_claude', return_value=None) as start_claude, patch.object(atticus, 'wait_commit', return_value=True), \
             patch.object(atticus, 'run_api_provider', return_value=reply) as run_api, patch.object(atticus, 'remember_turn'), patch.object(atticus, 'log_turn'), \
             patch.object(atticus, 'say') as say, patch.object(atticus.signal, 'signal'):
            atticus.main()
        start_claude.assert_called_once_with()
        run_api.assert_called_once_with('Explain a quasar')
        say.assert_called_once_with('✓', 'A concise answer.\nAnswered by openai (backup-model).')

    def test_account_preferences_reach_the_runtime_router(self):
        prefs = {'aiPrimary': 'openai', 'aiBackup1': 'claude-subscription', 'aiBackup2': 'none', 'aiFreeOnly': True,
                 'aiFailover': True, 'aiOpenAIModel': 'account-model'}
        expected = ProviderReply(ProviderId.OPENAI, model='account-model', text='Answer')
        with patch.object(atticus, 'pref', side_effect=lambda key, default: prefs.get(key, default)), \
             patch.object(atticus, 'ProviderRouter') as router_type:
            router_type.return_value.complete.return_value = expected
            reply = atticus.run_api_provider('What is a nebula?', {})
        self.assertEqual(reply, expected)
        policy = router_type.return_value.complete.call_args.args[1]
        self.assertEqual(policy.order, (ProviderId.OPENAI, ProviderId.CLAUDE_SUBSCRIPTION))


if __name__ == "__main__":
    unittest.main()
