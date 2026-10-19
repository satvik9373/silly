import json
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import action_engine
import atticus
import winctl


class MockExecutor:
    def __init__(self, apps=None, launch=True, arrange='moved', open_result=True):
        self._apps = apps if apps is not None else [{'name': 'Google Chrome'}, {'name': 'Notepad'}]
        self.launch_result = launch
        self.arrange_result = arrange
        self.open_result = open_result
        self.opened = []
        self.arranged = []

    def applications(self):
        return self._apps

    def launch(self, name):
        self.opened.append(('app', name))
        return self.launch_result

    def open_url(self, url):
        self.opened.append(('url', url))
        return self.open_result

    def open_in_browser(self, browser, url):
        self.opened.append(('browser', browser, url))
        return self.open_result

    def arrange(self, name, position, screen):
        self.arranged.append((name, position, screen))
        return self.arrange_result


class MockWindowsControl:
    def __init__(self, result=True, focused=False): self.calls, self.result, self.focused = [], result, focused
    def launch_url(self, browser, url): self.calls.append((browser, url)); return self.result
    def focus_app(self, name): self.calls.append(('focus', name)); return self.focused
    def launch(self, name): self.calls.append(('launch', name)); return self.result


class ActionEngineTests(unittest.TestCase):
    def registry(self, executor=None, locale=None):
        return action_engine.ActionRegistry(executor or MockExecutor(), locale)

    def test_open_application_resolves_alias_without_ai(self):
        executor = MockExecutor()
        route = action_engine.route_transcript('Open Chrome')
        result = self.registry(executor).execute(route.action_id, route.params)
        self.assertTrue(result.ok)
        self.assertEqual(executor.opened, [('app', 'Google Chrome')])

    def test_fast_deterministic_route_never_initializes_ai(self):
        route = action_engine.Route(True, 'open_application', {'name': 'Chrome'})
        result = action_engine.ActionResult(action_engine.Status.SUCCESS, 'Opened Google Chrome.', {'application': 'Google Chrome'})
        with tempfile.TemporaryDirectory() as root, \
             patch.object(atticus, 'DIR', root), patch.object(atticus, 'LAST', str(Path(root) / 'last_app')), \
             patch.object(atticus, 'route_action', return_value=(route, result)), \
             patch.object(atticus, 'start_claude', side_effect=AssertionError('AI must not be initialized')):
            self.assertEqual(atticus.fast('open chrome'), 'Opened Google Chrome.')

    def test_direct_search_remains_available_when_account_providers_are_unavailable(self):
        route = action_engine.Route(True, 'search_website', {'site': 'youtube', 'query': 'react tutorials'})
        result = action_engine.ActionResult(action_engine.Status.SUCCESS, 'Searched react tutorials on YouTube.')
        with tempfile.TemporaryDirectory() as root, \
             patch.object(atticus, 'DIR', root), patch.object(atticus, 'LAST', str(Path(root) / 'last_app')), \
             patch.object(atticus, 'route_action', return_value=(route, result)), \
             patch.object(atticus, 'plan', return_value={'ok': False, 'need': 'install'}), \
             patch.object(atticus, 'run_api_provider', side_effect=AssertionError('providers must not run')):
            self.assertEqual(atticus.fast('search youtube for react tutorials'), 'Searched react tutorials on YouTube.')

    def test_open_site_and_search_uses_variable_query_slots_without_ai(self):
        # These names are deliberately not aliases or implementation examples.
        for words, site, query in (
            ('Open YouTube and search for Kendrick Lamar', 'youtube', 'Kendrick Lamar'),
            ('Open YouTube and search for A. R. Rahman live 2026', 'youtube', 'A. R. Rahman live 2026'),
            ('Open Amazon and search for ergonomic split keyboard', 'amazon', 'ergonomic split keyboard'),
        ):
            route = action_engine.route_transcript(words)
            self.assertEqual((route.action_id, route.params), ('search_website', {'site': site, 'query': query}))
        executor = MockExecutor()
        route = action_engine.route_transcript('Open YouTube and search for Kendrick Lamar in Chrome')
        self.assertEqual(route.action_id, 'search_website_in_browser')
        result = self.registry(executor).execute(route.action_id, route.params)
        self.assertTrue(result.ok)
        self.assertEqual(executor.opened[-1], ('browser', 'Google Chrome', 'https://www.youtube.com/results?search_query=Kendrick+Lamar'))

    def test_finalized_wait_command_routes_before_provider_initialization(self):
        route = action_engine.Route(True, 'open_application', {'name': 'Chrome'})
        result = action_engine.ActionResult(action_engine.Status.SUCCESS, 'Opened Google Chrome.', {'application': 'Google Chrome'})
        with patch('sys.argv', ['silly.py', '--wait']), patch('sys.stdin', io.StringIO('Desktop\topen chrome\n')), \
             patch.object(atticus, 'look', return_value=[]), patch.object(atticus, 'licensed', return_value=True), \
             patch.object(atticus, 'route_action', return_value=(route, result)), \
             patch.object(atticus, 'pref', side_effect=lambda _key, default: default), \
             patch.object(atticus, 'ping'), patch.object(atticus, 'remember_turn'), patch.object(atticus, 'log_turn'), \
             patch.object(atticus, 'start_claude', side_effect=AssertionError('provider must not start')) as provider, \
             patch.object(atticus, 'say') as say:
            atticus.main()
        provider.assert_not_called()
        say.assert_called_once_with('✓', 'Opened Google Chrome.')

    def test_finalized_direct_command_does_not_require_a_provider_license(self):
        route = action_engine.Route(True, 'open_application', {'name': 'Chrome'})
        result = action_engine.ActionResult(action_engine.Status.SUCCESS, 'Opened Google Chrome.', {'application': 'Google Chrome'})
        with patch('sys.argv', ['silly.py', '--wait']), patch('sys.stdin', io.StringIO('Desktop\topen chrome\n')), \
             patch.dict(atticus.os.environ, {'ATTICUS_COMMIT': ''}), \
             patch.object(atticus, 'look', return_value=[]), patch.object(atticus, 'licensed', return_value=False), \
             patch.object(atticus, 'route_action', return_value=(route, result)), \
             patch.object(atticus, 'pref', side_effect=lambda _key, default: default), \
             patch.object(atticus, 'ping'), patch.object(atticus, 'remember_turn'), patch.object(atticus, 'log_turn'), \
             patch.object(atticus, 'start_claude', side_effect=AssertionError('provider must not start')) as provider, \
             patch.object(atticus, 'say') as say:
            atticus.main()
        provider.assert_not_called()
        say.assert_called_once_with('✓', 'Opened Google Chrome.')

    def test_finalized_typed_action_precedes_instant_and_provider_gates(self):
        result = action_engine.ActionResult(action_engine.Status.SUCCESS, 'Searched Raftaar music on Youtube.')
        with patch('sys.argv', ['silly.py', '--wait']), patch('sys.stdin', io.StringIO('Desktop\tSearch for Raftaar music on YouTube\n')), \
             patch.dict(atticus.os.environ, {'ATTICUS_COMMIT': 'missing-commit-marker'}, clear=False), \
             patch.object(atticus, 'route_action', return_value=(action_engine.Route(True, 'search_website', {'site': 'youtube', 'query': 'Raftaar music'}), result)), \
             patch.object(atticus, 'pref', side_effect=lambda key, default: False if key == 'instant' else default), \
             patch.object(atticus, 'licensed', return_value=False), patch.object(atticus, 'ping'), \
             patch.object(atticus, 'remember_turn'), patch.object(atticus, 'log_turn'), \
             patch.object(atticus, 'fast', side_effect=AssertionError('fast gate must not run first')), \
             patch.object(atticus, 'run_api_provider', side_effect=AssertionError('provider must not run')), \
             patch.object(atticus, 'start_claude', side_effect=AssertionError('Claude must not start')), \
             patch.object(atticus, 'say') as say:
            atticus.main()
        say.assert_called_once_with('✓', 'Searched Raftaar music on Youtube.')

    def test_finalized_approved_shortcut_never_uses_the_legacy_parser(self):
        approved = action_engine.ActionResult(action_engine.Status.SUCCESS, 'Opened Google Chrome.')
        with patch('sys.argv', ['silly.py', '--wait']), patch('sys.stdin', io.StringIO('Desktop\tmy work browser\n')), \
             patch.object(atticus, 'route_action', return_value=(action_engine.Route(False), None)), \
             patch.object(atticus, 'run_approved_action', return_value=approved), \
             patch.object(atticus, 'fast', side_effect=AssertionError('legacy parser must not run')), \
             patch.object(atticus, 'start_claude', side_effect=AssertionError('provider must not start')), \
             patch.object(atticus, 'ping'), patch.object(atticus, 'remember_turn'), patch.object(atticus, 'log_turn'), \
             patch.object(atticus, 'say') as say:
            atticus.main()
        say.assert_called_once_with('✓', 'Opened Google Chrome.')

    def test_typed_action_failure_is_retained_for_the_overlay(self):
        failure = action_engine.ActionResult(action_engine.Status.FAILURE, 'No matching application was found')
        with patch.object(atticus, 'route_action', return_value=(action_engine.Route(True, 'open_application', {'name': 'Missing'}), failure)):
            self.assertEqual(atticus.fast('open missing'), 'No matching application was found')
        self.assertEqual(atticus.fast.result.status, action_engine.Status.FAILURE)

    def test_missing_and_ambiguous_application_fail_truthfully(self):
        missing = self.registry(MockExecutor([])).execute('open_application', {'name': 'Missing'})
        ambiguous = self.registry(MockExecutor([{'name': 'Visual Studio'}, {'name': 'Visual Studio Code'}])).execute('open_application', {'name': 'Visual'})
        self.assertEqual(missing.status, action_engine.Status.FAILURE)
        self.assertEqual(ambiguous.status, action_engine.Status.FAILURE)
        self.assertIn('choices', ambiguous.data)

    def test_http_url_and_search_urls_are_validated_and_encoded(self):
        executor = MockExecutor()
        registry = self.registry(executor, 'www.amazon.co.uk')
        self.assertTrue(registry.execute('open_url', {'url': 'https://example.com/a?x=1'}).ok)
        for url in ('file:///C:/secret', 'https://user:pass@example.com/', 'https://example.com:bad/',
                    'https://example.com/\r\nstart calc', 'https://example.com\\cmd', 'https://example.com/"quoted"'):
            self.assertEqual(registry.execute('open_url', {'url': url}).status, action_engine.Status.FAILURE, url)
        self.assertTrue(registry.execute('search_website', {'site': 'youtube', 'query': 'lofi & code'}).ok)
        self.assertTrue(registry.execute('search_website', {'site': 'amazon', 'query': 'usb cable'}).ok)
        self.assertEqual(executor.opened[-2][1], 'https://www.youtube.com/results?search_query=lofi+%26+code')
        self.assertEqual(executor.opened[-1][1], 'https://www.amazon.co.uk/s?k=usb+cable')
        self.assertEqual(registry.execute('search_website', {'site': 'youtube', 'query': 'hello\x00world'}).status, action_engine.Status.FAILURE)
        browser_search = registry.execute('search_website_in_browser', {'site': 'amazon', 'query': 'Kendrick & keyboard', 'browser': 'Chrome'})
        self.assertTrue(browser_search.ok)
        self.assertEqual(executor.opened[-1], ('browser', 'Google Chrome', 'https://www.amazon.co.uk/s?k=Kendrick+%26+keyboard'))

    def test_navigation_hinglish_and_requested_browser_are_deterministic(self):
        cases = {
            'Open YouTube.': ('open_url', {'url': 'https://www.youtube.com/'}),
            'Go to GitHub.': ('open_url', {'url': 'https://github.com/'}),
            'Search the web for latest React tutorial': ('search_website', {'site': 'google', 'query': 'latest React tutorial'}),
            'Search YouTube for React tutorials': ('search_website', {'site': 'youtube', 'query': 'React tutorials'}),
            'Play Raftaar music on YouTube': ('search_website', {'site': 'youtube', 'query': 'Raftaar'}),
            'YouTube pe Raftaar ke songs chalao': ('search_website', {'site': 'youtube', 'query': 'Raftaar'}),
            'YouTube par React tutorials search karo': ('search_website', {'site': 'youtube', 'query': 'React tutorials'}),
            'यूट्यूब पर रफ़्तार के गाने चलाओ': ('search_website', {'site': 'youtube', 'query': 'रफ़्तार'}),
            'यूट्यूब पर रिएक्ट ट्यूटोरियल खोजो': ('search_website', {'site': 'youtube', 'query': 'रिएक्ट ट्यूटोरियल'}),
        }
        for words, expected in cases.items():
            route = action_engine.route_transcript(words)
            self.assertEqual((route.action_id, route.params), expected)
        executor = MockExecutor()
        route = action_engine.route_transcript('Search YouTube for React tutorials in Chrome')
        result = self.registry(executor).execute(route.action_id, route.params)
        self.assertTrue(result.ok)
        self.assertEqual(executor.opened[-1], ('browser', 'Google Chrome', 'https://www.youtube.com/results?search_query=React+tutorials'))
        for words, expected_url in (
            ('Go to YouTube and search for React tutorials in Chrome', 'https://www.youtube.com/results?search_query=React+tutorials'),
            ('Open YouTube in Chrome', 'https://www.youtube.com/'),
        ):
            route = action_engine.route_transcript(words)
            result = self.registry(executor).execute(route.action_id, route.params)
            self.assertTrue(result.ok)
            self.assertEqual(executor.opened[-1], ('browser', 'Google Chrome', expected_url))

    def test_held_out_navigation_and_search_corpus_preserves_domain_queries(self):
        # These paraphrases are deliberately separate from the implementation
        # examples so the deterministic grammar is exercised rather than a set
        # of hard-coded product names.
        cases = {
            'Search for Raftaar music on YouTube': ('search_website', {'site': 'youtube', 'query': 'Raftaar music'}),
            'Search the web for portfolio-satvik.versal.app': ('search_website', {'site': 'google', 'query': 'portfolio-satvik.versal.app'}),
            'Search the web for satvikchaturvedi.me': ('search_website', {'site': 'google', 'query': 'satvikchaturvedi.me'}),
            'Search Google for satvikchaturvedi.me': ('search_website', {'site': 'google', 'query': 'satvikchaturvedi.me'}),
            'Search for café music on YouTube': ('search_website', {'site': 'youtube', 'query': 'café music'}),
            'Open portfolio-satvik.versal.app': ('open_url', {'url': 'https://portfolio-satvik.versal.app'}),
            'Open satvikchaturvedi.me': ('open_url', {'url': 'https://satvikchaturvedi.me'}),
            'Open a new Chrome tab': ('open_browser_url', {'browser': 'chrome', 'url': 'https://www.google.com/'}),
        }
        for words, expected in cases.items():
            route = action_engine.route_transcript(words)
            self.assertEqual((route.action_id, route.params), expected, words)
        executor = MockExecutor()
        route = action_engine.route_transcript('Search for résumé-tips.example on YouTube')
        result = self.registry(executor).execute(route.action_id, route.params)
        self.assertTrue(result.ok)
        self.assertEqual(executor.opened[-1], ('url', 'https://www.youtube.com/results?search_query=r%C3%A9sum%C3%A9-tips.example'))

    def test_hindi_script_query_is_encoded_without_rewriting_it(self):
        executor = MockExecutor()
        route = action_engine.route_transcript('यूट्यूब पर रफ़्तार के गाने चलाओ')
        result = self.registry(executor).execute(route.action_id, route.params)
        self.assertTrue(result.ok)
        self.assertEqual(executor.opened[-1], ('url', 'https://www.youtube.com/results?search_query=%E0%A4%B0%E0%A4%AB%E0%A4%BC%E0%A5%8D%E0%A4%A4%E0%A4%BE%E0%A4%B0'))

    def test_browser_launch_failure_is_a_typed_failure(self):
        executor = MockExecutor(open_result=False)
        route = action_engine.route_transcript('Open YouTube in Chrome')
        result = self.registry(executor).execute(route.action_id, route.params)
        self.assertEqual(result.status, action_engine.Status.FAILURE)
        self.assertIn('Could not open', result.message)
        self.assertEqual(executor.opened, [('browser', 'Google Chrome', 'https://www.youtube.com/')])

    def test_windows_browser_executor_dispatches_to_safe_launcher(self):
        control = MockWindowsControl()
        executor = action_engine.WindowsExecutor(control)
        self.assertTrue(executor.open_in_browser('Google Chrome', 'https://www.youtube.com/'))
        self.assertEqual(control.calls, [('Google Chrome', 'https://www.youtube.com/')])

    def test_windows_executor_focuses_an_existing_application_before_launching(self):
        focused = MockWindowsControl(focused=True)
        self.assertTrue(action_engine.WindowsExecutor(focused).launch('Google Chrome'))
        self.assertEqual(focused.calls, [('focus', 'Google Chrome')])
        missing = MockWindowsControl(focused=False)
        self.assertTrue(action_engine.WindowsExecutor(missing).launch('Google Chrome'))
        self.assertEqual(missing.calls, [('focus', 'Google Chrome'), ('launch', 'Google Chrome')])

    def test_focus_path_skips_start_menu_discovery_for_a_direct_process_match(self):
        candidate = {'hwnd': 42, 'title': 'Untitled - Notepad', 'exe': r'C:\Windows\System32\notepad.exe', 'proc': 'notepad'}
        with patch.object(winctl, 'window_candidates', return_value=[candidate]), \
             patch.object(winctl, 'apps', side_effect=AssertionError('Start-menu discovery must not delay a direct focus')), \
             patch.object(winctl, 'bring', return_value=True) as bring:
            self.assertTrue(winctl.focus_app('Notepad'))
        bring.assert_called_once_with(42)

    def test_unknown_navigation_does_not_open_an_unrelated_site(self):
        self.assertFalse(action_engine.route_transcript('take me somewhere nice').matched)
        self.assertEqual(action_engine.route_transcript('open https://bad example').action_id, 'open_application')

    def test_polite_unseen_navigation_phrases_stay_typed(self):
        cases = {
            'Hey Silly, please open YouTube on Edge': ('open_browser_url', {'browser': 'edge', 'url': 'https://www.youtube.com/'}),
            'Could you open a new tab in Chrome': ('open_browser_url', {'browser': 'chrome', 'url': 'https://www.google.com/'}),
            'Please switch to Chrome': ('open_application', {'name': 'Chrome'}),
        }
        for words, expected in cases.items():
            route = action_engine.route_transcript(words)
            self.assertEqual((route.action_id, route.params), expected)

    def test_window_positions_are_typed_and_validated(self):
        executor = MockExecutor()
        result = self.registry(executor).execute('arrange_window', {'application': 'Notepad', 'position': 'maximized', 'screen': 'current'})
        self.assertTrue(result.ok)
        self.assertEqual(executor.arranged, [('Notepad', 'full', 'current')])
        invalid = self.registry(executor).execute('arrange_window', {'application': 'Notepad', 'position': 'diagonal', 'screen': 'current'})
        self.assertEqual(invalid.status, action_engine.Status.FAILURE)

    def test_registry_rejects_unknown_extra_and_malformed_actions(self):
        registry = self.registry()
        self.assertEqual(registry.execute('powershell', {}).status, action_engine.Status.FAILURE)
        self.assertEqual(registry.execute('open_url', {'url': 'https://example.com', 'extra': 'x'}).status, action_engine.Status.FAILURE)
        self.assertEqual(registry.execute('open_application', {'name': 3}).status, action_engine.Status.FAILURE)

    def test_confirmation_and_terminal_states_are_explicit(self):
        spec = action_engine.ActionSpec('confirm_test', {'name': str}, action_engine.Permission.CONFIRM,
            lambda p, e: action_engine.ActionResult(action_engine.Status.PARTIAL, 'partly done'))
        registry = self.registry()
        registry._specs['confirm_test'] = spec
        self.assertEqual(registry.execute('confirm_test', {'name': 'x'}).status, action_engine.Status.CANCELLED)
        self.assertEqual(registry.execute('confirm_test', {'name': 'x'}, confirmed=True).status, action_engine.Status.PARTIAL)

    def test_route_instruments_selection_action_and_verification(self):
        executor = MockExecutor()
        with patch.object(atticus, 'action_registry', return_value=self.registry(executor)):
            route, result = atticus.route_action('search youtube for test query')
        self.assertTrue(route.matched and result.ok)
        metrics = atticus.action_metrics()
        self.assertIsNotNone(metrics['transcript_finalization_ms'])
        self.assertIsNotNone(metrics['route_selection_ms'])
        self.assertIsNotNone(metrics['first_action_ms'])
        self.assertIsNotNone(metrics['action_verification_ms'])

    def test_approved_shortcuts_are_typed_and_legacy_shell_is_not_executed(self):
        with tempfile.TemporaryDirectory() as root, patch.object(atticus, 'APPROVED_ACTIONS', str(Path(root) / 'approved.json')):
            executor = MockExecutor()
            with patch.object(atticus, 'action_registry', return_value=self.registry(executor)):
                self.assertTrue(atticus.save_approved_action('open chrome now', {'id': 'open_application', 'params': {'name': 'Chrome'}}, 'Opened Chrome.'))
                result = atticus.run_approved_action('open chrome now', executor)
            self.assertTrue(result.ok)
            Path(root, 'approved.json').write_text(json.dumps({'unsafe': {'actions': [{'id': 'bash', 'params': {'command': 'powershell'}}]}}), encoding='utf-8')
            self.assertEqual(atticus.run_approved_action('unsafe', executor).status, action_engine.Status.FAILURE)

    def test_ai_path_has_no_arbitrary_shell_execution_tools(self):
        source = Path(atticus.__file__).read_text(encoding='utf-8')
        self.assertIn("'WebSearch,WebFetch'", source)
        self.assertNotIn("'Bash,Read,WebSearch,WebFetch'", source)
        self.assertIn('command-string shortcuts are disabled', source)
        self.assertIn('watch actions are disabled', source)
        self.assertIn('read-only WebSearch and WebFetch tools', atticus.SYSTEM)
        self.assertNotIn('Bash', atticus.SYSTEM)
        self.assertIn('cannot run shell commands', atticus.SYSTEM)


if __name__ == '__main__':
    unittest.main()
