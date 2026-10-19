"""Regression checks for Silly's installation and runtime boundaries."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SillyIdentityTests(unittest.TestCase):
    def text(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_application_identity_and_isolated_storage(self):
        project = self.text("win/Atticus/Atticus.csproj")
        paths = self.text("win/Atticus/Prefs.cs")
        self.assertIn("<AssemblyName>Silly</AssemblyName>", project)
        self.assertIn("<Product>Silly</Product>", project)
        self.assertIn('Environment.GetEnvironmentVariable("SILLY_DIR")', paths)
        self.assertIn('"Silly"', paths)
        self.assertIn('"silly.json"', paths)
        self.assertIn('"silly.py"', paths)
        self.assertNotIn('Environment.GetEnvironmentVariable("ATTICUS_DIR")', paths)

    def test_runtime_identifiers_are_silly_only(self):
        program = self.text("win/Atticus/Program.cs")
        windows = self.text("win/Atticus/Windows.cs")
        self.assertIn('@"Local\\Silly"', program)
        self.assertIn('const string PipeName = "silly.v1"', program)
        self.assertIn('run.SetValue("Silly"', windows)
        self.assertIn('run.DeleteValue("Silly", false)', windows)
        self.assertNotIn('@"Local\\Atticus"', program)
        self.assertNotIn('PipeName = "atticus"', program)
        self.assertNotIn('case "update":', program)

    def test_build_only_manages_silly_at_its_own_path(self):
        build = self.text("build.ps1")
        self.assertIn("'Programs\\Silly'", build)
        self.assertIn("Get-Process Silly", build)
        self.assertIn("$_.Path -eq (Join-Path $app 'Silly.exe')", build)
        self.assertIn('Programs\\Silly.lnk', build)
        self.assertIn("-Name Silly", build)
        self.assertNotIn("Get-Process Atticus", build)
        self.assertNotIn("Stop-Process -Name", build)

    def test_normal_build_promotes_a_complete_silly_candidate_with_rollback(self):
        build = self.text("build.ps1")
        self.assertIn('$dest = "$app.next"', build)
        self.assertIn('$old = "$app.old"', build)
        self.assertIn('Move-Item $app $old -ErrorAction Stop', build)
        self.assertIn('Move-Item $dest $app -ErrorAction Stop', build)
        self.assertIn('Silly could not promote the completed build', build)
        self.assertIn("Could not clear Silly's previous staged candidate", build)
        self.assertIn("Could not clear Silly's previous rollback directory", build)

    def test_installer_stages_the_typed_python_runtime(self):
        build = self.text("build.ps1")
        # silly.py imports these from its own directory after installation;
        # omit neither module from the staged candidate.
        for module in ("action_engine.py", "ai_provider_router.py", "openai_siwc.py", "winctl.py"):
            self.assertIn(f"Copy-Item {module}", build)

    def test_staged_python_layout_imports_without_the_source_tree(self):
        with tempfile.TemporaryDirectory() as temporary:
            staged = Path(temporary) / "Silly"
            staged.mkdir()
            # build.ps1 deliberately renames the installed brain to silly.py.
            shutil.copy2(ROOT / "atticus.py", staged / "silly.py")
            for module in ("action_engine.py", "ai_provider_router.py", "openai_siwc.py", "winctl.py"):
                shutil.copy2(ROOT / module, staged / module)
            shutil.copytree(ROOT / "integrations", staged / "integrations")
            environment = dict(os.environ)
            environment["SILLY_DIR"] = str(Path(temporary) / "data")
            environment.pop("GNANI_API_KEY", None)
            result = subprocess.run([sys.executable, str(staged / "silly.py"), "--help"], capture_output=True, text=True,
                                    timeout=15, env=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Silly for Windows", result.stdout)

    def test_development_launcher_uses_only_a_temporary_python_environment(self):
        launcher = self.text("scripts/run-dev.ps1")
        self.assertIn("$venv = Join-Path $run 'venv'", launcher)
        self.assertIn("-m venv $venv", launcher)
        self.assertIn("requirements.txt", launcher)
        self.assertIn("$env:SILLY_DIR = $config", launcher)
        self.assertNotIn("build.ps1", launcher)
        self.assertNotIn("CurrentVersion\\Run", launcher)

    def test_cloud_speech_is_opt_in_and_visibly_disclosed(self):
        prefs = self.text("win/Atticus/Prefs.cs")
        settings = self.text("ui/settings.html")
        onboarding = self.text("ui/onboarding.html")
        windows = self.text("win/Atticus/Windows.cs")
        self.assertIn('["speechProvider"] = "local"', prefs)
        self.assertIn('["ttsProvider"] = "windows"', prefs)
        self.assertIn('["cloudFallback"] = "local"', prefs)
        self.assertIn('Gnani Cloud sends microphone audio to Gnani for transcription.', settings)
        self.assertIn('Gnani Cloud sends response text to Gnani.', settings)
        self.assertNotIn('Gnani Cloud', onboarding)
        self.assertIn('k == "speechProvider" && v is not ("local" or "gnani")', windows)
        self.assertIn('k == "ttsProvider" && v is not ("windows" or "gnani")', windows)

    def test_gnani_development_key_does_not_reach_python_or_ai_helpers(self):
        prefs = self.text("win/Atticus/Prefs.cs")
        assistant = self.text("atticus.py")
        updater = self.text("win/Atticus/Updater.cs")
        windows = self.text("win/Atticus/Windows.cs")
        self.assertIn('ChildEnvironment.RemoveSecrets(si)', prefs)
        self.assertIn('env=shim_env()', assistant)
        self.assertGreaterEqual(updater.count("ChildEnvironment.RemoveSecrets(si)"), 2)
        self.assertNotIn('FixPlan()', windows)
        self.assertNotIn('ChildEnvironment.RemoveSecrets(setup)', windows)

    def test_updates_are_explicitly_opt_in(self):
        prefs = self.text("win/Atticus/Prefs.cs")
        updater = self.text("win/Atticus/Updater.cs")
        windows = self.text("win/Atticus/Windows.cs")
        self.assertIn('["autoUpdate"] = false', prefs)
        self.assertIn('if (!Prefs.Bool("autoUpdate")) return;', updater)
        self.assertIn('if (Pending && Prefs.Bool("autoUpdate"))', updater)
        self.assertIn('StagedStatus(Prefs.Bool("autoUpdate"))', updater)
        self.assertIn('Updater.StagedStatus(Prefs.Bool("autoUpdate"))', windows)

    def test_no_charge_provider_policy_is_explicit_and_persisted(self):
        prefs = self.text("win/Atticus/Prefs.cs")
        windows = self.text("win/Atticus/Windows.cs")
        settings = self.text("ui/settings.html")
        for key in ("aiClaudeSubscriptionNoCharge",):
            self.assertIn(f'["{key}"] = false', prefs)
            self.assertIn(f'data-k="{key}"', settings)
        self.assertIn('Prefs.Defaults.ContainsKey(k)', windows)
        self.assertIn('v is not bool', windows)

    def test_claude_subscription_is_a_separate_supported_route(self):
        router = self.text("ai_provider_router.py")
        settings = self.text("ui/settings.html")
        self.assertIn('CLAUDE_SUBSCRIPTION = "claude-subscription"', router)
        self.assertIn('Claude subscription', settings)
        self.assertIn('data-option-key="aiBackup"', settings)
        self.assertIn('never marks a started request retryable', router)

    def test_chatgpt_plan_connection_uses_silly_storage_and_is_not_an_api_key(self):
        prefs = self.text("win/Atticus/Prefs.cs")
        settings = self.text("ui/settings.html")
        build = self.text("build.ps1")
        provider = self.text("openai_siwc.py")
        self.assertNotIn('aiOpenAIAuthMode', prefs)
        self.assertIn('ChatGPT plan', settings)
        self.assertNotIn('OpenAI API key', settings)
        self.assertIn('Copy-Item openai_siwc.py', build)
        self.assertIn('Silly/OpenAIChatGPT/', provider)
        self.assertIn('chatgpt.tokens.use.direct', provider)
        self.assertNotIn('backend-api', provider)

    def test_visible_ui_has_no_reference_branding(self):
        for path in (ROOT / "ui").glob("*.html"):
            visible = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.S)
            visible = re.sub(r"//.*", "", visible)
            self.assertNotIn("Atticus", visible, path.name)
            self.assertIn("Silly", visible, path.name)

    def test_product_runtime_has_no_telemetry_transport(self):
        assistant = self.text("atticus.py")
        readme = self.text("README.md")
        self.assertNotIn("SILLY_POSTHOG_KEY", assistant)
        self.assertNotIn("us.i.posthog.com", assistant)
        self.assertIn("no telemetry transport", readme)


if __name__ == "__main__":
    unittest.main()
