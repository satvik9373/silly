import base64
import json
import time
import unittest
from urllib.parse import parse_qs, urlparse

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from ai_provider_router import FailureKind, OpenAIChatGPTProvider, ProviderId, ProviderPolicy, ProviderRouter
from openai_siwc import (AccountStore, ChatGPTPlan, MemoryCredentialStore,
                         PendingAuthorization, PLAN_SCOPE, REQUIRED_SCOPES,
                         SiwcError, begin_authorization, validate_callback,
                         validate_id_token)


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


def signed_token(client, nonce, subject='person-1', email='person@example.test', expires=None):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    header = b64(json.dumps({'alg': 'RS256', 'kid': 'test'}, separators=(',', ':')).encode())
    body = b64(json.dumps({'iss': 'https://auth.openai.com', 'aud': client, 'nonce': nonce, 'sub': subject, 'email': email,
                           'exp': int(expires if expires is not None else time.time() + 3600)}, separators=(',', ':')).encode())
    signed = (header + '.' + body).encode()
    sig = private.sign(signed, padding.PKCS1v15(), hashes.SHA256())
    nums = private.public_key().public_numbers()
    jwks = {'keys': [{'kty': 'RSA', 'kid': 'test', 'n': b64(nums.n.to_bytes((nums.n.bit_length() + 7) // 8, 'big')),
                      'e': b64(nums.e.to_bytes((nums.e.bit_length() + 7) // 8, 'big'))}]}
    return signed.decode() + '.' + b64(sig), jwks


class FakeHttp:
    def __init__(self): self.forms, self.streams, self.calls, self.jwks = [], [], [], {}
    def form(self, url, form, timeout): self.calls.append(('form', url, dict(form))); return self.forms.pop(0)
    def json(self, url, headers, timeout): self.calls.append(('json', url, dict(headers))); return self.jwks[url]
    def stream(self, url, headers, payload, timeout): self.calls.append(('stream', url, dict(headers), dict(payload))); return self.streams.pop(0)


class SiwcTests(unittest.TestCase):
    def setUp(self): self.store = AccountStore(MemoryCredentialStore())

    def test_authorization_has_stable_host_pkce_loopback_and_required_scopes(self):
        first, url = begin_authorization(self.store, 43821)
        second, _ = begin_authorization(self.store, 43822)
        query = parse_qs(urlparse(url).query)
        self.assertEqual(first.host_id, second.host_id)
        self.assertEqual(query['client_id'], ['dynamic_agent_client'])
        self.assertEqual(query['agent_name_hint'], ['Silly'])
        self.assertEqual(query['redirect_uri'], ['http://127.0.0.1:43821/auth/callback'])
        self.assertNotIn('localhost', query['redirect_uri'][0])
        self.assertEqual(set(query['scope'][0].split()), REQUIRED_SCOPES)
        self.assertEqual(query['resource'], ['https://api.openai.com/v1'])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        self.assertNotEqual(first.state, second.state)

    def test_callback_rejects_wrong_state_and_permission_decline(self):
        pending, _ = begin_authorization(self.store, 4000)
        with self.assertRaises(SiwcError): validate_callback(pending, {'state': 'wrong', 'code': 'x', 'client_id': 'oaiapp_x'})
        with self.assertRaisesRegex(SiwcError, 'declined'): validate_callback(pending, {'state': pending.state, 'error': 'access_denied'})
        self.assertEqual(validate_callback(pending, {'state': pending.state, 'code': 'x', 'client_id': 'oaiapp_x'}), ('x', 'oaiapp_x'))

    def test_signed_identity_requires_matching_issuer_audience_nonce_and_expiry(self):
        token, jwks = signed_token('oaiapp_a', 'nonce')
        self.assertEqual(validate_id_token(token, 'oaiapp_a', 'nonce', jwks)['sub'], 'person-1')
        with self.assertRaises(SiwcError): validate_id_token(token, 'oaiapp_a', 'other', jwks)
        expired, keys = signed_token('oaiapp_a', 'nonce', expires=time.time() - 1)
        with self.assertRaises(SiwcError): validate_id_token(expired, 'oaiapp_a', 'nonce', keys)

    def test_exchange_saves_separate_account_and_marks_permission_absent_without_enabling_plan(self):
        pending, _ = begin_authorization(self.store, 4000)
        token, jwks = signed_token('oaiapp_a', pending.nonce)
        http = FakeHttp(); http.forms = [(200, {'access_token': 'access', 'refresh_token': 'refresh', 'id_token': token, 'expires_in': 3600, 'scope': 'openid profile email offline_access resource.invoke'})]
        http.jwks = {'https://jwks.test': (200, jwks), 'https://auth.openai.com/.well-known/openid-configuration': (200, {'jwks_uri': 'https://jwks.test'})}
        plan = ChatGPTPlan(self.store, http)
        status = plan.exchange(pending, {'state': pending.state, 'code': 'code', 'client_id': 'oaiapp_a'})
        self.assertTrue(status['connected']); self.assertFalse(status['planEnabled'])
        record = self.store.active()
        self.assertEqual(record['client_id'], 'oaiapp_a')
        self.assertNotIn('access', json.dumps(self.store._index()))

    def test_refresh_rotates_tokens_and_stream_requires_completed_event(self):
        self.store.save({'client_id': 'oaiapp_a', 'subject': 'p', 'email': 'p@example.test', 'id_token': 'hint', 'access_token': 'old',
                         'refresh_token': 'old-refresh', 'scopes': list(REQUIRED_SCOPES), 'expires_at': 0})
        http = FakeHttp(); http.forms = [(200, {'access_token': 'new', 'refresh_token': 'new-refresh', 'expires_in': 3600, 'scope': ' '.join(REQUIRED_SCOPES)})]
        http.streams = [(200, ['data: {"type":"response.output_text.delta","delta":"Hello "}', 'data: {"type":"response.output_text.delta","delta":"there"}', 'data: {"type":"response.completed"}'], {})]
        plan = ChatGPTPlan(self.store, http)
        text, model = plan.complete('hi', 'gpt-test')
        self.assertEqual((text, model), ('Hello there', 'gpt-test'))
        stream = next(x for x in http.calls if x[0] == 'stream')
        self.assertEqual(stream[3]['store'], False); self.assertEqual(stream[3]['stream'], True)
        self.assertEqual(self.store.active()['refresh_token'], 'new-refresh')

    def test_plan_permission_absence_and_incomplete_stream_do_not_produce_a_reply(self):
        self.store.save({'client_id': 'oaiapp_a', 'subject': 'p', 'access_token': 'a', 'refresh_token': 'r', 'scopes': ['openid'], 'expires_at': time.time() + 300})
        http = FakeHttp(); plan = ChatGPTPlan(self.store, http)
        with self.assertRaisesRegex(SiwcError, 'did not grant'): plan.complete('hi', 'gpt-test')
        self.assertEqual(http.calls, [])
        self.store.save({'client_id': 'oaiapp_a', 'subject': 'p', 'access_token': 'a', 'refresh_token': 'r', 'scopes': list(REQUIRED_SCOPES), 'expires_at': time.time() + 300})
        http.streams = [(200, ['data: {"type":"response.output_text.delta","delta":"partial"}'], {})]
        with self.assertRaisesRegex(SiwcError, 'incomplete'): plan.complete('hi', 'gpt-test')

    def test_model_catalog_uses_only_server_listed_models(self):
        self.store.save({'client_id': 'oaiapp_a', 'subject': 'p', 'access_token': 'a', 'refresh_token': 'r', 'scopes': list(REQUIRED_SCOPES), 'expires_at': time.time() + 300})
        http = FakeHttp(); http.jwks = {'https://api.openai.com/v1/models': (200, {'models': [
            {'slug': 'shown', 'display_name': 'Shown', 'visibility': 'list'}, {'slug': 'hidden', 'visibility': 'internal'}]})}
        self.assertEqual(ChatGPTPlan(self.store, http).models(), [{'slug': 'shown', 'display_name': 'Shown'}])

    def test_model_catalog_accepts_standard_data_response_without_exposing_hidden_models(self):
        self.store.save({'client_id': 'oaiapp_a', 'subject': 'p', 'access_token': 'a', 'refresh_token': 'r',
                         'scopes': list(REQUIRED_SCOPES), 'expires_at': time.time() + 300})
        http = FakeHttp()
        http.jwks = {'https://api.openai.com/v1/models': (200, {'data': [
            {'id': 'chatgpt-plan-model'}, {'id': 'internal-model', 'visibility': 'internal'}]})}
        self.assertEqual(ChatGPTPlan(self.store, http).models(),
                         [{'slug': 'chatgpt-plan-model', 'display_name': 'chatgpt-plan-model'}])

    def test_availability_requires_plan_scope_and_a_nonempty_model_catalog(self):
        self.store.save({'client_id': 'oaiapp_a', 'subject': 'p', 'email': 'p@example.test',
                         'id_token': 'id', 'access_token': 'a', 'refresh_token': 'r',
                         'scopes': list(REQUIRED_SCOPES), 'expires_at': time.time() + 300})
        http = FakeHttp()
        http.jwks = {'https://api.openai.com/v1/models': (200, {'models': [
            {'slug': 'shown', 'display_name': 'Shown', 'visibility': 'list'}]})}
        state = ChatGPTPlan(self.store, http).availability()
        self.assertEqual(state['state'], 'ready')
        self.assertTrue(state['modelsLoaded'])
        self.assertFalse(state['reasoningVerified'])
        http.jwks = {'https://api.openai.com/v1/models': (503, {})}
        state = ChatGPTPlan(self.store, http).availability()
        self.assertEqual(state['state'], 'unavailable')
        self.assertNotIn('access', json.dumps(state))

    def test_availability_does_not_call_models_without_required_scope(self):
        self.store.save({'client_id': 'oaiapp_a', 'subject': 'p', 'id_token': 'id',
                         'access_token': 'a', 'refresh_token': 'r', 'scopes': ['openid'],
                         'expires_at': time.time() + 300})
        http = FakeHttp()
        state = ChatGPTPlan(self.store, http).availability()
        self.assertEqual(state['state'], 'unavailable')
        self.assertIn('permission', state['message'])
        self.assertEqual(http.calls, [])

    def test_router_cannot_turn_plan_text_into_actions(self):
        class FakePlan:
            def complete(self, prompt, model, timeout): return 'Plain explanation.', model
        provider = OpenAIChatGPTProvider(FakePlan(), 'gpt-test')
        reply = ProviderRouter({ProviderId.OPENAI: provider}, {}).complete('explain', ProviderPolicy((ProviderId.OPENAI,), free_only=False))
        self.assertTrue(reply.ok); self.assertEqual(reply.text, 'Plain explanation.')
        self.assertFalse(hasattr(reply, 'actions'))
        class MissingPlan:
            def complete(self, *args): raise SiwcError('Continue with ChatGPT in Settings before using ChatGPT plan usage.')
        failure = ProviderRouter({ProviderId.OPENAI: OpenAIChatGPTProvider(MissingPlan(), 'gpt-test')}, {}).complete('explain', ProviderPolicy((ProviderId.OPENAI,), free_only=False))
        self.assertEqual(failure.failure.kind, FailureKind.AUTH)


if __name__ == '__main__': unittest.main()
