from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UiSimplificationTests(unittest.TestCase):
    def text(self, path):
        return (ROOT / path).read_text(encoding="utf-8")

    def test_settings_uses_locally_bundled_web_awesome_selects(self):
        settings = self.text("ui/settings.html")
        self.assertIn('vendor/webawesome/webawesome.loader.js', settings)
        self.assertIn('<wa-select', settings)
        self.assertNotIn('<select', settings)
        self.assertTrue((ROOT / 'ui/vendor/webawesome/webawesome.loader.js').is_file())
        self.assertTrue((ROOT / 'ui/vendor/webawesome/LICENSE.md').is_file())

    def test_api_key_and_generic_integration_surfaces_are_not_exposed(self):
        settings = self.text("ui/settings.html")
        windows = self.text("win/Atticus/Windows.cs")
        for text in ('Anthropic API key', 'OpenAI API key', 'Gemini API key', 'data-s="integrations"', 'Add your own'):
            self.assertNotIn(text, settings)
        for handler in ('case "saveAiKey"', 'case "intCustom"', 'case "intSave"'):
            self.assertNotIn(handler, windows)

    def test_ui_does_not_advertise_a_telemetry_opt_in_without_a_transport(self):
        settings = self.text("ui/settings.html")
        overlay = self.text("ui/ui.html")
        native_overlay = self.text("win/Atticus/Overlay.cs")
        for text in (settings, overlay, native_overlay):
            self.assertNotIn("Help improve Silly", text)
            self.assertNotIn("Help make Silly better", text)
            self.assertNotIn("! improve", text)

    def test_local_font_contract_and_recursive_asset_copy_are_explicit(self):
        settings = self.text("ui/settings.html")
        onboarding = self.text("ui/onboarding.html")
        overlay = self.text("ui/ui.html")
        build = self.text("build.ps1")
        release_validation = self.text("scripts/validate-release.ps1")
        for text in (settings, onboarding, overlay):
            self.assertIn('Satoshi-Variable.ttf', text)
            self.assertIn('font-weight: 300 500', text)
        self.assertIn('Copy-Item ui\\* "$dest\\ui" -Recurse -Force', build)
        self.assertTrue((ROOT / 'ui/assets/fonts/README.md').is_file())
        self.assertTrue((ROOT / 'ui/assets/fonts/Satoshi-Fontshare-EULA.txt').is_file())
        self.assertIn('Fontshare EULA', self.text('ui/assets/fonts/Satoshi-Fontshare-EULA.txt'))
        self.assertIn('Satoshi-Fontshare-EULA.txt', release_validation)

    def test_onboarding_stays_focused_on_voice_essentials(self):
        onboarding = self.text("ui/onboarding.html")
        native = self.text("win/Atticus/Windows.cs")
        program = self.text("win/Atticus/Program.cs")
        self.assertNotIn('Claude AI (optional)', onboarding)
        self.assertNotIn('p-claude', onboarding)
        self.assertNotIn('ob.plan', native)
        self.assertNotIn('OnboardingWindow.Plan', program)
        self.assertIn('data-k="aiPrimary"', self.text("ui/settings.html"))
        self.assertIn('data-option-key="aiPrimary"', self.text("ui/settings.html"))
        self.assertIn("['mic', 'Microphone'", onboarding)
        self.assertIn("['speech', 'Speech Model'", onboarding)
        self.assertIn('Voice setup complete', onboarding)

    def test_satoshi_is_explicit_for_controls_and_web_components(self):
        onboarding = self.text("ui/onboarding.html")
        settings = self.text("ui/settings.html")
        overlay = self.text("ui/ui.html")
        self.assertIn('button, input, textarea, select, kbd { font-family: var(--font-sans); }', onboarding)
        self.assertIn('--wa-font-family-body: var(--silly-font)', settings)
        self.assertIn('wa-select, wa-option {', settings)
        self.assertIn('--wa-font-family-body: var(--silly-font)', settings)
        self.assertIn('button, input, textarea, select, kbd { font-family: "Satoshi"', overlay)
        for text in (onboarding, settings, overlay):
            self.assertNotRegex(text, r'font-weight:\s*[6-9]')

    def test_sidebar_uses_bundled_lucide_icons(self):
        settings = self.text("ui/settings.html")
        self.assertIn('vendor/lucide/icons/settings.svg', settings)
        self.assertNotIn('<i class="ni" style=', settings)
        self.assertTrue((ROOT / 'ui/vendor/lucide/LICENSE').is_file())


if __name__ == '__main__':
    unittest.main()
