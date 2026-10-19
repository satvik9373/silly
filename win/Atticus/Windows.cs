// The Settings window (ui\settings.html) and the first-run setup window (ui\onboarding.html).
using System.Diagnostics;
using System.Text.Json;
using Microsoft.Web.WebView2.WinForms;

namespace Atticus;

class PageWindow : Form
{
    protected WebView2 web;
    readonly string page, handler;
    protected PageWindow(string page, string handler, string title, int w, int h)
    {
        this.page = page; this.handler = handler;
        Text = title; StartPosition = FormStartPosition.CenterScreen; BackColor = Color.Black;
        ClientSize = new Size((int)(w * DeviceDpi / 96.0), (int)(h * DeviceDpi / 96.0));
        MinimizeBox = true; MaximizeBox = false; FormBorderStyle = FormBorderStyle.FixedSingle;
        var ico = Path.Combine(Paths.App, "ui", "AppIcon.ico");
        if (File.Exists(ico)) Icon = new Icon(ico);
    }
    protected override void OnHandleCreated(EventArgs e) { base.OnHandleCreated(e); Native.Backdrop(Handle, acrylic: false, round: true); }
    protected async Task Ensure()
    {
        if (web != null) return;
        web = await Web.Load(this, page, (n, b) => { if (n == handler) OnMessage(b); }, true);
        web.NavigationCompleted += (_, _) => Loaded();
    }
    protected virtual void Loaded() { }
    protected virtual void OnMessage(JsonElement b) { }
    public void Js(string s) => Web.Js(web, s);
    protected void Send(string call, object v) => Program.Post(() => Js($"{call}({Web.Json(v)})"));
    protected void Raise() { if (WindowState == FormWindowState.Minimized) WindowState = FormWindowState.Normal; Show(); Activate(); Native.SetForegroundWindow(Handle); }
}

sealed class SettingsWindow : PageWindow
{
    string tab = "";
    System.Windows.Forms.Timer perms;
    readonly Dictionary<string, bool> providerReady = new();
    readonly Dictionary<string, HashSet<string>> providerModels = new();
    public SettingsWindow() : base("settings.html", "st", "Silly Settings", 780, 560)
    {
        FormClosing += (_, e) => { if (e.CloseReason == CloseReason.UserClosing) { e.Cancel = true; if (Hooks.Recording) Done(0, 0, null); Hide(); perms?.Stop(); } };
    }

    public async void Open(string t = "")
    {
        tab = t;
        Raise();
        await Ensure();
        Refresh2(); if (t != "") { Js($"st.tab('{t}')"); tab = ""; }
        perms ??= new System.Windows.Forms.Timer { Interval = 1500 };
        perms.Tick -= Perms; perms.Tick += Perms; perms.Start();
    }
    void Perms(object s, EventArgs e) { if (Visible) Send("st.perms", OnboardingWindow.Perms()); }

    protected override void Loaded() { Push(); Refresh2(); Send("st.perms", OnboardingWindow.Perms()); if (tab != "") { Js($"st.tab('{tab}')"); tab = ""; } }

    public void Push()   // the settings, and the app icon for the sidebar
    {
        if (web == null) return;
        GnaniCredentials.TryGet(out _, out var credentialError);
        var credentialSource = Environment.GetEnvironmentVariable("GNANI_API_KEY") is { Length: > 0 } ? "Environment variable" : credentialError == "" ? "Windows Credential Manager" : "Not configured";
        var d = new Dictionary<string, object> {
            ["prefs"] = Prefs.D, ["version"] = Paths.Install("version"), ["update"] = Updater.Status == "" ? (Updater.Pending ? Updater.StagedStatus(Prefs.Bool("autoUpdate")) : "") : Updater.Status, ["sounds"] = Sound.All(),
            ["ttsCatalog"] = GnaniVoiceCatalog.ForUi(), ["options"] = SettingsOptions.ForUi(),
            ["voiceDiagnostics"] = new { sttPreferred = Prefs.Str("speechProvider"), sttActive = Program.Speech.ActiveProvider, ttsPreferred = Prefs.Str("ttsProvider"), ttsActive = Voice.LastProvider, ttsRequest = Voice.LastRequest, model = Prefs.Str("gnaniTtsModel"), voice = Prefs.Str("gnaniTtsVoice"), language = Prefs.Str("gnaniTtsLanguage"), credentialSource, sttError = Program.Speech.LastProviderError, ttsError = Voice.LastError }
        };
        var png = Path.Combine(Paths.App, "ui", "AppIcon.png");
        if (File.Exists(png)) d["icon"] = "data:image/png;base64," + Convert.ToBase64String(File.ReadAllBytes(png));
        Js($"st.load({Web.Json(d)})");
    }

    static class SettingsOptions
    {
        static object[] Options(params (string value, string label)[] values) =>
            values.Select(x => (object)new { value = x.value, label = x.label }).ToArray();

        public static Dictionary<string, object[]> ForUi() => new()
        {
            ["speechLanguages"] = Options(("en-IN", "English (India)"), ("hi-IN", "Hindi"), ("bn-IN", "Bengali"), ("gu-IN", "Gujarati"),
                ("kn-IN", "Kannada"), ("ml-IN", "Malayalam"), ("mr-IN", "Marathi"), ("pa-IN", "Punjabi"), ("ta-IN", "Tamil"), ("te-IN", "Telugu")),
            ["ttsModels"] = Options(("timbre-v3.0", "Timbre v3.0"), ("timbre-v2.5", "Timbre v2.5")),
            ["ttsLanguages"] = Options(("en-IN", "en-IN"), ("auto", "auto"), ("hi-en", "hi-en"), ("hi-IN", "hi-IN"), ("ta-IN", "ta-IN"),
                ("te-IN", "te-IN"), ("kn-IN", "kn-IN"), ("ml-IN", "ml-IN"), ("mr-IN", "mr-IN"), ("pa-IN", "pa-IN"), ("bn-IN", "bn-IN"), ("gu-IN", "gu-IN")),
            ["vocabularyStrengths"] = Options(("0.5", "0.5"), ("1.0", "1.0"), ("1.5", "1.5"), ("2.0", "2.0")),
            ["aiPrimary"] = Array.Empty<object>(),
            ["aiBackup"] = Options(("none", "No backup"))
        };
    }

    // usage, saved rules, Claude plan: atticus.py --state (it runs Claude Code, so off the UI thread)
    void Refresh2() => Task.Run(() =>
    {
        var s = Py.Run(new[] { "--state" });
        if (!s.StartsWith("{")) return;
        try
        {
            using var doc = JsonDocument.Parse(s);
            var rows = doc.RootElement.GetProperty("providers").GetProperty("providers");
            var ready = new Dictionary<string, bool>();
            var models = new Dictionary<string, HashSet<string>>();
            foreach (var row in rows.EnumerateArray())
            {
                var id = row.GetProperty("id").GetString() ?? "";
                ready[id] = row.GetProperty("state").GetString() == "ready";
                var modelIds = new HashSet<string>();
                if (row.TryGetProperty("models", out var list))
                    foreach (var model in list.EnumerateArray())
                        if (model.TryGetProperty("slug", out var slug)) modelIds.Add(slug.GetString() ?? "");
                models[id] = modelIds;
            }
            Program.Post(() =>
            {
                providerReady.Clear(); foreach (var pair in ready) providerReady[pair.Key] = pair.Value;
                providerModels.Clear(); foreach (var pair in models) providerModels[pair.Key] = pair.Value;
                Js($"st.state({s})");
            });
        }
        catch { Program.Post(() => Js($"st.state({s})")); }
    });

    bool ProviderReady(string id) => providerReady.GetValueOrDefault(id);

    void Helper(params string[] args) => Task.Run(() => { Py.Run(args); Program.Post(Refresh2); });

    public void Apply(string k, object v)   // one setting changed, from this window or by voice (atticus.py --set)
    {
        if (!Prefs.Defaults.ContainsKey(k)) return;
        if (k == "gnaniTtsModel")
        {
            var model = v as string;
            if (!GnaniVoiceCatalog.IsKnownModel(model)) return;
            Prefs.Set(k, model);
            if (!GnaniVoiceCatalog.IsVoiceForModel(model, Prefs.Str("gnaniTtsVoice"))) Prefs.Set("gnaniTtsVoice", GnaniVoiceCatalog.DefaultVoice(model, Prefs.Str("gnaniTtsLanguage")));
            Push(); return;
        }
        if (k == "gnaniTtsVoice" && !GnaniVoiceCatalog.IsVoiceForModel(Prefs.Str("gnaniTtsModel"), v as string)) return;
        if (k == "gnaniTtsLanguage" && !GnaniVoiceCatalog.IsKnownLanguage(v as string)) return;
        if (k == "speechProvider" && v is not ("local" or "gnani")) return;
        if (k == "gnaniLanguage" && !GnaniSttOptions.IsSupportedLanguage(v as string)) return;
        if (k == "ttsProvider" && v is not ("windows" or "gnani")) return;
        if (k == "aiPrimary" && (v is not ("claude-code" or "openai") || !ProviderReady(v as string == "openai" ? "openai" : "claude-subscription"))) return;
        if ((k == "aiBackup1" || k == "aiBackup2") && v is not ("none" or "claude-subscription" or "openai")) return;
        if ((k == "aiBackup1" || k == "aiBackup2") && v is string backup && backup != "none" && !ProviderReady(backup == "openai" ? "openai" : "claude-subscription")) return;
        if (k == "aiClaudeSubscriptionNoCharge" && v is not bool) return;
        if (k == "aiOpenAIModel" && (v is not string providerModel || !ProviderReady("openai") || !providerModels.GetValueOrDefault("openai", new()).Contains(providerModel) || providerModel.Length > 128 || !System.Text.RegularExpressions.Regex.IsMatch(providerModel, @"^[A-Za-z0-9._:-]*$"))) return;
        Prefs.Set(k, v);
        if (k == "speak" && v is false) Voice.Shush();
        if (k == "menuIcon") Program.Tray.Visible = v is true;
        if (k == "paused" && v is true) Program.Box.Close(false);
        if (k == "safe") Program.Box.js("mode", v is true);
        if (k == "speechModel") _ = Program.Speech.Load();
        if (k == "login") Startup(v is true);
    }

    public static void Startup(bool on)
    {
        using var run = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run");
        if (on) run.SetValue("Silly", $"\"{Environment.ProcessPath}\""); else run.DeleteValue("Silly", false);
    }

    void Record()
    {
        if (Hooks.Recording) return;
        Hooks.RecordingMods = m => Program.Post(() => Js($"st.rec({Web.Json(m)})"));
        Hooks.Recorded = (vk, mods, label) => Program.Post(() => Done(vk, mods, label));
        Hooks.Recording = true;
    }

    void Done(int vk, int mods, string label)
    {
        Hooks.Recording = false;
        if (label != null && vk != 0) { Prefs.Set("hotkeyCode", vk); Prefs.Set("hotkeyMods", mods); Prefs.Set("hotkeyLabel", label); }
        Push();
    }

    protected override void OnDeactivate(EventArgs e) { base.OnDeactivate(e); if (Hooks.Recording) Done(0, 0, null); }

    protected override void OnMessage(JsonElement b)
    {
        if (b.ValueKind != JsonValueKind.Object || !b.TryGetProperty("do", out var d)) return;
        string S(string k) => b.TryGetProperty(k, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
        switch (d.GetString())
        {
            case "set":
                if (S("k") is not { } k || !b.TryGetProperty("v", out var v)) return;
                Apply(k, v.ValueKind switch { JsonValueKind.True => true, JsonValueKind.False => false, JsonValueKind.Number => v.GetDouble(), _ => (object)v.GetString() });
                break;
            case "saveGnaniKey":
                if (S("value") is { } key)
                {
                    var ok = GnaniCredentials.Save(key, out var error);
                    var message = ok ? "Gnani key saved securely in Windows Credential Manager." : error;
                    Js($"st.gnaniKeyResult({Web.Json(message)})");
                }
                break;
            case "connectChatGPT":
                Js("st.chatgptResult('Opening ChatGPT sign-in in your browser…')");
                Task.Run(() => { var r = Py.Run(new[] { "--openai-siwc", "connect" }, 330); var message = ChatGPTMessage(r, "ChatGPT sign-in did not complete."); Program.Post(() => { Js($"st.chatgptResult({Web.Json(message)})"); Refresh2(); }); });
                break;
            case "disconnectChatGPT":
                Task.Run(() => { var r = Py.Run(new[] { "--openai-siwc", "disconnect" }, 30); var message = ChatGPTMessage(r, "ChatGPT disconnect did not complete."); Program.Post(() => { Js($"st.chatgptResult({Web.Json(message)})"); Refresh2(); }); });
                break;
            case "refreshChatGPTModels":
                Js("st.chatgptResult('Refreshing models for the selected ChatGPT account…')");
                Task.Run(() => { Refresh2(); });
                break;
            case "testChatGPT":
                Js("st.chatgptResult('Testing one explicit ChatGPT reasoning request…')");
                Task.Run(() => { var r = Py.Run(new[] { "--provider-test", "chatgpt" }, 40); Program.Post(() => { Js($"st.chatgptResult({Web.Json(ChatGPTMessage(r, "ChatGPT connection test did not complete."))})"); Refresh2(); }); });
                break;
            case "testClaude":
                Js("st.claudeResult('Testing one explicit Claude reasoning request…')");
                Task.Run(() => { var r = Py.Run(new[] { "--provider-test", "claude" }, 40); Program.Post(() => { Js($"st.claudeResult({Web.Json(ProviderMessage(r, "Claude connection test did not complete."))})"); Refresh2(); }); });
                break;
            case "testGnaniVoice":
                Js("st.voiceTest('Testing selected Gnani voice…')");
                Voice.TestGnani(result => { Js($"st.voiceTest({Web.Json(result.Ok ? $"Gnani voice played: {Prefs.Str("gnaniTtsModel")} / {Prefs.Str("gnaniTtsVoice")}" : result.Error)})"); Push(); });
                break;
            case "record": Record(); break;
            case "cancelRecord": if (Hooks.Recording) Done(0, 0, null); break;
            case "unlearn": if (S("say") is { } say) Helper("--unlearn", say); break;
            case "checkUpdate": Updater.Check(Push); break;
            case "github": { var repository = Paths.Install("repository"); if (repository != "") Web.Open(repository); break; }
            case "resetHotkey": Prefs.Set("hotkeyCode", 0x20); Prefs.Set("hotkeyMods", 3); Prefs.Set("hotkeyLabel", "Ctrl+Alt+Space"); Push(); break;
            case "preview": if (S("sound") is { } n) Sound.Play(n, Prefs.Num("volume") * 2); break;
            case "setup": Program.Onboarding.Open(); break;
            case "openLog": if (File.Exists(Paths.Log)) Web.Open(Paths.Log); break;
            case "clearRecent": try { File.Delete(Paths.Recent); } catch { } Program.Box.lastDone = DateTime.MinValue; break;
            case "me": if (S("what") is { } w && S("text") is { } t) Helper("--me", w, t); break;
            case "forget": case "remember": if (S("line") is { } line) Helper("--" + d.GetString(), line); break;
            case "grant": if (S("id") is { } id) Program.Onboarding.Grant(id); break;
            case "quit": Application.Exit(); break;
        }
    }

    // The helper returns only safe account/status text, never a token. Parsing
    // here lets declined consent and eligibility errors remain visible instead
    // of being reported as a generic completed browser operation.
    static string ChatGPTMessage(string json, string fallback)
    {
        try
        {
            using var d = JsonDocument.Parse(json);
            if (d.RootElement.TryGetProperty("message", out var message) && message.ValueKind == JsonValueKind.String)
                return message.GetString() ?? fallback;
            return d.RootElement.TryGetProperty("account", out var account) && account.ValueKind == JsonValueKind.String
                ? account.GetString() ?? fallback : fallback;
        }
        catch { return fallback; }
    }

    static string ProviderMessage(string json, string fallback)
    {
        try
        {
            using var d = JsonDocument.Parse(json);
            return d.RootElement.TryGetProperty("message", out var message) && message.ValueKind == JsonValueKind.String
                ? message.GetString() ?? fallback : fallback;
        }
        catch { return fallback; }
    }
}

sealed class OnboardingWindow : PageWindow
{
    System.Windows.Forms.Timer timer;
    bool downloading;
    public OnboardingWindow() : base("onboarding.html", "ob", "Welcome to Silly", 640, 640)
    {
        FormClosing += (_, e) => { if (e.CloseReason == CloseReason.UserClosing) { e.Cancel = true; Hide(); timer?.Stop(); } };
    }

    public async void Open()
    {
        Raise();
        await Ensure();
        int tick = 0;
        timer ??= new System.Windows.Forms.Timer { Interval = 50 };   // keys and permissions refresh while visible
        timer.Tick += (_, _) =>
        {
            if (!Visible) return;
            Js($"ob.keys({(Native.Down(Native.VK_CONTROL) ? "true" : "false")}, {(Native.Down(Native.VK_MENU) ? "true" : "false")})");
            tick++;
            if (tick % 20 == 1) Push();
        };
        timer.Start();
    }

    void Push()
    {
        Send("ob.set", Perms());
        Js($"ob.mode({(Prefs.Str("talkMode") == "toggle" ? "true" : "false")})");
    }

    public static Dictionary<string, bool> Perms() => new() { ["mic"] = Speech.MicAllowed(), ["speech"] = Program.Speech.Ready };

    public void Tried() => Js("ob.tried()");

    public void Grant(string id)
    {
        switch (id)
        {
            case "mic": Web.Open("ms-settings:privacy-microphone"); break;
            case "speech": GetModel(); break;
        }
    }

    async void GetModel()   // the speech model, once: progress shows in the row
    {
        if (downloading || File.Exists(Paths.Model)) return;
        downloading = true;
        var ok = await Speech.Download(p => Program.Post(() => Js($"ob.progress && ob.progress('speech', {p:0.###})")));
        downloading = false;
        if (ok) await Program.Speech.Load();
        Push();
        Program.Settings.Js("st.perms && st.perms(" + Web.Json(Perms()) + ")");
    }

    protected override void OnMessage(JsonElement b)
    {
        if (b.ValueKind != JsonValueKind.Object) return;
        if (b.TryGetProperty("do", out var d) && d.GetString() == "done") { Prefs.Set("onboarded", true); Hide(); timer?.Stop(); return; }
        if (b.TryGetProperty("id", out var id)) Grant(id.GetString() ?? "");
    }
}
