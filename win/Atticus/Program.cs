// Atticus for Windows: a tray app. Hold Ctrl+Alt+Space, talk, let go. atticus.py (the brain) does the work through Claude Code.
// Build and install: .\build.ps1 (starts at login from HKCU\...\Run).
using System.IO.Pipes;
using System.Text.Json;
using System.Text;
using NAudio.Wave;

namespace Atticus;

static class Program
{
    public static Overlay Box;
    public static SettingsWindow Settings;
    public static OnboardingWindow Onboarding;
    public static Tray Tray;
    public static Speech Speech = new();
    static SynchronizationContext ui;

    [STAThread]
    static void Main(string[] args)
    {
        if (args.SequenceEqual(new[] { "--selftest" }))
        {
            Check(Overlay.TranscriptKey(" Open   Notes. ") == Overlay.TranscriptKey("open notes"));
            Check(Overlay.TranscriptKey("calculate 1.5") != Overlay.TranscriptKey("calculate 15"));
            Check(Overlay.TranscriptKey("search a b") != Overlay.TranscriptKey("search ab"));
            Check(Speech.Clean(" [BLANK_AUDIO] Open notepad. ") == "Open notepad." && Speech.Clean("Thank you.") == "");
            Check(Hooks.Label(0x20, 3) == "Ctrl+Alt+Space" && Hooks.Label(0x71, 0) == "F2");
            Check(!Updater.ShouldActivateStagedUpdate(false) && Updater.ShouldActivateStagedUpdate(true));
            Check(Updater.StagedStatus(false).Contains("Enable automatic updates") && Updater.StagedStatus(true).Contains("Restarting"));
            var child = new System.Diagnostics.ProcessStartInfo();
            child.Environment["GNANI_API_KEY"] = "mock-key"; ChildEnvironment.RemoveSecrets(child);
            Check(!child.Environment.ContainsKey("GNANI_API_KEY"));
            Check(!GnaniSttOptions.TryCreate("", "en-IN", out _, out var credentialError) && credentialError.Contains("needs a key"));
            Check(GnaniSttOptions.TryCreate("mock-key", "", out var mockOptions, out _) && mockOptions.Language == "en-IN");
            Check(!GnaniSttOptions.TryCreate("mock-key", "hinglish", out _, out _));
            Check(!GnaniSttOptions.TryCreate("mock-key", "mixed", out _, out _) && GnaniSttOptions.TryCreate("mock-key", "hi-IN", out _, out _));
            Check(GnaniSttOptions.TryVocabulary("YouTube, Raftaar, Silly", "1.0", out var vocabulary, out var strength, out _) && vocabulary.Contains("Raftaar") && strength == "1.0");
            Check(!GnaniSttOptions.TryVocabulary("Visual Studio Code", "1.0", out _, out _, out _));
            var headers = (mockOptions with { MinSilence = 350, Vocabulary = vocabulary, VocabularyStrength = strength }).Headers();
            Check(headers["x-api-key-id"] == "mock-key" && headers["lang_code"] == "en-IN" && headers["x-sample-rate"] == "16000" && headers["x-format"] == "verbatim" && headers["x-min-silence-ms"] == "350" && headers["x-min-speech-ms"] == "100" && headers["x-min-segment-ms"] == "100" && headers.ContainsKey("x-bias-list") && headers["x-bias-score"] == "1.0");
            Check(GnaniSttOptions.SilenceFramesFor(350) == 12 && GnaniSttOptions.SilenceFramesFor(100) == 5);
            string error;
            var frames = new GnaniPcmFramer().Add(new byte[2048]).ToArray();
            Check(frames.Length == 2 && frames.All(f => f.Length == GnaniSttOptions.FrameBytes));
            var tailFramer = new GnaniPcmFramer();
            Check(tailFramer.Add(new byte[GnaniSttOptions.FrameBytes + 2]).Count() == 1 && tailFramer.Flush().Length == GnaniSttOptions.FrameBytes && tailFramer.Flush().Length == 0);
            Check(GnaniSttHandshake.TryAccept("{\"type\":\"connected\",\"config\":{\"sample_rate\":16000,\"chunk_size\":512}}", out error));
            Check(!GnaniSttHandshake.TryAccept("{\"type\":\"connected\",\"config\":{\"sample_rate\":8000,\"chunk_size\":512}}", out error) && error.Contains("unsupported audio format"));
            Check(!GnaniSttHandshake.TryAccept("{\"type\":\"error\",\"message\":\"invalid API key\"}", out error) && error.Contains("rejected the saved key"));
            var segments = new GnaniTranscriptAccumulator(); string words;
            Check(segments.AddServerMessage("{\"type\":\"transcript\",\"segment_id\":\"a\",\"segment_index\":0,\"text\":\"Open\"}", out words, out error) && words == "Open");
            Check(!segments.AddServerMessage("{\"type\":\"transcript\",\"segment_id\":\"a\",\"segment_index\":0,\"text\":\"Open\"}", out words, out error));
            Check(segments.AddServerMessage("{\"type\":\"transcript\",\"segment_id\":\"a\",\"segment_index\":0,\"text\":\"Open Notepad\"}", out words, out error) && words == "Open Notepad");
            Check(segments.AddServerMessage("{\"type\":\"transcript\",\"segment_id\":\"b\",\"segment_index\":1,\"text\":\"please\"}", out words, out error) && words == "Open Notepad please");
            Check(!segments.AddServerMessage("{\"type\":\"error\",\"message\":\"quota exhausted\"}", out words, out error) && error.Contains("quota is exhausted"));
            Check(GnaniErrors.SttServer("invalid API key").Contains("rejected the saved key") && GnaniErrors.SttServer("timeout").Contains("timed out"));
            Check(!segments.AddServerMessage("not-json", out words, out error) && error.Contains("invalid transcript"));
            Check(GnaniSttSession.UserError(new OperationCanceledException()).Contains("timed out"));
            Check(GnaniSttSession.UserError(new System.Net.WebSockets.WebSocketException()).Contains("Could not connect"));
            Check(GnaniTtsOptions.TryCreate("mock-key", "timbre-v3.0", "Shivani", "en-IN", 1, 15, out var mockTts, out _));
            var normalRequest = new GnaniTtsRequest(mockTts, "Opened Notepad.");
            var testRequest = new GnaniTtsRequest(mockTts, "Hello. This is your selected Silly voice.");
            Check(normalRequest.Configuration == testRequest.Configuration && normalRequest.Configuration == "timbre-v3.0 / Shivani / en-IN / 1.00x");
            using (var payload = JsonDocument.Parse(new GnaniTtsProvider(mockTts).RequestJson(normalRequest))) Check(payload.RootElement.GetProperty("model").GetString() == "timbre-v3.0" && payload.RootElement.GetProperty("voice").GetString() == "Shivani" && payload.RootElement.GetProperty("language").GetString() == "en-IN" && payload.RootElement.GetProperty("audio_config").GetProperty("container").GetString() == "raw");
            Check(GnaniTtsOptions.TryCreate("mock-key", "timbre-v2.5", "Kaveri", "en-IN", 1, 15, out _, out _));
            Check(!GnaniTtsOptions.TryCreate("mock-key", "timbre-v3.0", "Kaveri", "en-IN", 1, 15, out _, out _));
            Check(GnaniVoiceCatalog.DefaultVoice("timbre-v2.5", "hi-en") == "Poorvi" && JsonSerializer.Serialize(GnaniVoiceCatalog.ForUi()["timbre-v3.0"]).Contains("\"value\":\"Shivani\""));
            Check(!GnaniTtsOptions.TryCreate("mock-key", "bad", "Shivani", "en-IN", 1, 15, out _, out _));
            var tts = new GnaniTtsMessageAccumulator();
            Check(tts.AddServerMessage("{\"type\":\"start\"}", out var chunk, out error) && chunk.Length == 0);
            Check(tts.AddServerMessage("{\"type\":\"audio\",\"data\":{\"chunk_index\":0,\"audio\":\"AQI=\",\"is_final\":false}}", out chunk, out error) && chunk.Length == 2);
            Check(!tts.AddServerMessage("{\"type\":\"audio\",\"data\":{\"chunk_index\":0,\"audio\":\"AQI=\",\"is_final\":false}}", out chunk, out error) && error.Contains("out of order"));
            var completed = new GnaniTtsMessageAccumulator();
            Check(completed.AddServerMessage("{\"type\":\"audio\",\"data\":{\"chunk_index\":0,\"audio\":\"AQI=\",\"is_final\":false}}", out chunk, out error));
            Check(completed.AddServerMessage("{\"type\":\"complete\",\"data\":{\"chunk_index\":1,\"audio\":\"\",\"is_final\":true}}", out chunk, out error) && completed.Complete);
            var ttsError = new GnaniTtsMessageAccumulator();
            Check(!ttsError.AddServerMessage("{\"type\":\"error\",\"message\":\"quota exhausted\"}", out chunk, out error) && error.Contains("quota is exhausted"));
            var reply = AssistantResponse.Success("Opened Notepad."); var replies = new ResponseDeduplicator();
            Check(reply.ForPreferences().Status == ResponseStatus.Success && replies.TryAccept(reply) && !replies.TryAccept(reply));
            var fakeSpeaker = new SelfTestResponseSpeaker(); var delivery = new ResponseDelivery(fakeSpeaker);
            Check(delivery.Deliver(AssistantResponse.Success("Opened Notepad."), _ => { }, _ => { }) && fakeSpeaker.Calls == 1);
            Check(!delivery.Deliver(AssistantResponse.Success("Opened Notepad."), _ => { }, _ => { }) && fakeSpeaker.Calls == 1); // duplicate completion cannot speak twice
            Check(delivery.Deliver(AssistantResponse.Failure("Could not open Notepad."), _ => { }, _ => { }) && fakeSpeaker.Calls == 2);
            fakeSpeaker.Result = new SpeechOutputResult(true, "Muted"); delivery.Reset(); Check(delivery.Deliver(AssistantResponse.Success("Muted reply."), _ => { }, _ => { }) && fakeSpeaker.Calls == 3);
            Check(SpeechOutputPlan.Select(true, false, true) == "Windows local" && SpeechOutputPlan.Select(true, false, false) == "Unavailable");
            Console.WriteLine("native selftest ok"); return;
        }
        if (args.SequenceEqual(new[] { "--webselftest" }))
        {
            ApplicationConfiguration.Initialize();
            Environment.SetEnvironmentVariable("SILLY_WEB_DIAGNOSTICS", "1");
            Environment.Exit(WebRuntimeSelfTest.Run());
        }
        if (args.Length >= 2 && args[0] == "--text") Environment.Exit(WindowText.Run(args[1], args.Length > 2 ? args[2] : ""));
        if (args.Length == 2 && args[0] == "--transcribe")   // diagnostics: a 16 kHz mono WAV through the same speech path
        {
            Speech.Load().Wait();
            if (!Speech.Ready) { Console.Error.WriteLine("no speech model: " + Paths.Model + " " + Speech.Error); Environment.Exit(1); }
            using var r = new NAudio.Wave.AudioFileReader(args[1]);
            var all = new List<float>(); var buf = new float[16000]; int n;
            while ((n = ((NAudio.Wave.ISampleProvider)r).Read(buf.AsSpan())) > 0) all.AddRange(buf.Take(n));
            var t0 = DateTime.Now;
            Console.WriteLine(Speech.TranscribeOnce(all.ToArray()).Result + $"  [{(DateTime.Now - t0).TotalSeconds:0.00} s]");
            return;
        }
        // Development runs are deliberately isolated from an installed or older
        // development copy; production keeps one stable Silly instance.
        var mutexName = Environment.GetEnvironmentVariable("SILLY_DEVELOPMENT") == "1" ? @"Local\Silly.Dev." + Environment.ProcessId : @"Local\Silly";
        using var one = new Mutex(true, mutexName, out var first);
        if (!first) { Send("open"); return; }   // already running: it shows Settings (or setup)
        ApplicationConfiguration.Initialize();
        Application.SetColorMode(SystemColorMode.Dark);
        var ctx = new ApplicationContext();
        Application.Idle += Started;
        void Started(object s, EventArgs e)
        {
            Application.Idle -= Started;
            _ = Launch();
        }
        Application.Run(ctx);
        Box?.Hush(); Voice.Shush();
    }

    static void Check(bool ok) { if (!ok) { Console.Error.WriteLine("native selftest failed"); Environment.Exit(1); } }

    static async Task Launch()
    {
        ui = SynchronizationContext.Current;
        Directory.CreateDirectory(Paths.Config);
        Settings = new SettingsWindow();
        Onboarding = new OnboardingWindow();
        Tray = new Tray();
        Box = new Overlay(Speech);
        await Box.Init();
        Hooks.Install();
        _ = Speech.Load();
        Listen();
        if (Environment.GetEnvironmentVariable("SILLY_DEVELOPMENT") != "1") Updater.Schedule();
        if (!Prefs.Bool("onboarded") || Speech.ModelRequired && !File.Exists(Paths.Model)) Onboarding.Open();
        if (Environment.GetEnvironmentVariable("SILLY_DEMO") is { Length: > 0 } demo) { await Task.Delay(1500); Box.Demo(demo); }
    }

    public static void Post(Action a) => ui?.Post(_ => a(), null);

    public static void Err(string line)
    {
        try { File.AppendAllText(Path.Combine(Paths.Config, "app.err"), line + "\n"); } catch { }
    }

    // atticus.py and a second copy of Atticus talk to the running app through a named pipe: one line each.
    const string PipeName = "silly.v1";
    static void Listen() => Task.Run(async () =>
    {
        while (true)
        {
            try
            {
                using var s = new NamedPipeServerStream(PipeName, PipeDirection.In, 1, PipeTransmissionMode.Byte, PipeOptions.Asynchronous);
                await s.WaitForConnectionAsync();
                using var r = new StreamReader(s, Encoding.UTF8);
                var line = await r.ReadLineAsync() ?? "";
                Post(() => Command(line));
            }
            catch { await Task.Delay(500); }
        }
    });

    static void Command(string line)
    {
        var p = line.Split('\t', 2);
        switch (p[0])
        {
            case "notify": Tray.Notify(p.Length > 1 ? p[1] : ""); break;
            case "open": if (Prefs.Bool("onboarded")) Settings.Open(); else Onboarding.Open(); break;
        }
    }

    static void Send(string line)
    {
        try { using var c = new NamedPipeClientStream(".", PipeName, PipeDirection.Out); c.Connect(1500); var b = Encoding.UTF8.GetBytes(line + "\n"); c.Write(b); } catch { }
    }
}

sealed class SelfTestResponseSpeaker : IResponseSpeaker
{
    public int Calls { get; private set; }
    public SpeechOutputResult Result = new(true, "Gnani Cloud");
    public void Say(AssistantResponse response, Action<SpeechOutputResult> done, Action<string> firstAudio) { Calls++; firstAudio("Gnani Cloud"); done(Result); }
}

// Read answers aloud in Windows' voice. Esc or the shortcut stops it.
static class Voice
{
    static System.Speech.Synthesis.SpeechSynthesizer synth;
    static CancellationTokenSource active;
    static RawPcmPlayer player;
    public static bool Speaking;
    public static string LastProvider { get; private set; } = "Not spoken yet";
    public static string LastError { get; private set; } = "";
    // This is configuration only: never include API keys or the spoken reply.
    public static string LastRequest { get; private set; } = "No speech request yet";
    public static void Say(AssistantResponse response, Action<SpeechOutputResult> done, Action<string> firstAudio = null)
    {
        Shush();
        if (!Prefs.Bool("speak") || !response.ShouldSpeak)
        {
            LastRequest = "Normal reply: muted";
            LastProvider = "Muted"; LastError = "";
            done(new(true, "Muted")); return;
        }
        var mine = active = new CancellationTokenSource();
        Speaking = true;
        _ = Task.Run(async () =>
        {
            var r = await SpeakAsync(response.ForPreferences().SpokenText, mine.Token, firstAudio);
            Program.Post(() => { if (active != mine) return; Speaking = false; active.Dispose(); active = null; LastProvider = r.Provider; LastError = r.Error; done(r); });
        });
    }

    // A user-triggered diagnostic. It never runs at startup and never hides a
    // Gnani failure behind Windows speech: this verifies the selected cloud voice.
    public static void TestGnani(Action<SpeechOutputResult> done)
    {
        Shush();
        if (!GnaniTtsOptions.TryFromPrefs(out var options, out var error))
        {
            LastRequest = "Test Voice: Gnani Cloud (configuration unavailable)";
            LastProvider = "Gnani Cloud"; LastError = error;
            done(new(false, "Gnani Cloud", error)); return;
        }
        LastRequest = "Test Voice: Gnani Cloud (" + new GnaniTtsRequest(options, "").Configuration + ")";
        var mine = active = new CancellationTokenSource(); Speaking = true;
        _ = Task.Run(async () =>
        {
            var result = await SpeakGnaniAsync(options, "Hello. This is your selected Silly voice.", mine.Token, firstAudio: null);
            Program.Post(() => { if (active != mine) return; Speaking = false; active.Dispose(); active = null; LastProvider = result.Provider; LastError = result.Error; done(result); });
        });
    }

    static async Task<SpeechOutputResult> SpeakAsync(string text, CancellationToken cancellationToken, Action<string> firstAudio)
    {
        var configError = "";
        GnaniTtsOptions options = null;
        var useGnani = Prefs.Str("ttsProvider") == "gnani";
        if (useGnani) GnaniTtsOptions.TryFromPrefs(out options, out configError);
        if (useGnani && options != null)
        {
            LastRequest = "Normal reply: Gnani Cloud (" + new GnaniTtsRequest(options, "").Configuration + ")";
            var result = await SpeakGnaniAsync(options, text, cancellationToken, firstAudio);
            if (result.Ok) return result;
            if (Prefs.Bool("ttsFallback"))
            {
                var fallback = await SpeakWindowsAsync(text, cancellationToken, firstAudio);
                return fallback with { Error = result.Error };
            }
            return result;
        }
        if (useGnani)
        {
            LastRequest = "Normal reply: Gnani Cloud (configuration unavailable)";
            if (!Prefs.Bool("ttsFallback")) return new(false, "Gnani Cloud", configError);
            var fallback = await SpeakWindowsAsync(text, cancellationToken, firstAudio);
            // Keep the requested provider's reason for Settings diagnostics even
            // when local speech successfully keeps the reply audible.
            return fallback with { Error = configError };
        }
        LastRequest = "Normal reply: Windows local";
        return await SpeakWindowsAsync(text, cancellationToken, firstAudio);
    }

    // Both normal replies and the explicitly user-triggered Test Voice control
    // use this exact transport/playback path. The only difference is whether
    // the caller is permitted to select Windows local fallback.
    static async Task<SpeechOutputResult> SpeakGnaniAsync(GnaniTtsOptions options, string text, CancellationToken cancellationToken, Action<string> firstAudio)
    {
        using var raw = new RawPcmPlayer(); player = raw;
        var first = false;
        var result = await new GnaniTtsProvider(options).SpeakAsync(text, cancellationToken, b =>
        {
            raw.Add(b);
            if (!first) { first = true; Program.Post(() => firstAudio?.Invoke($"Gnani Cloud ({options.Model} / {options.Voice})")); }
        });
        if (result.Ok)
        {
            try { await raw.DrainAsync(cancellationToken); }
            catch (OperationCanceledException) { result = new(false, "Gnani Cloud", "Speech was cancelled."); }
        }
        player = null;
        return result;
    }

    static Task<SpeechOutputResult> SpeakWindowsAsync(string text, CancellationToken token, Action<string> firstAudio)
    {
        var done = new TaskCompletionSource<SpeechOutputResult>(TaskCreationOptions.RunContinuationsAsynchronously);
        Program.Post(() =>
        {
            if (token.IsCancellationRequested) { done.TrySetResult(new(false, "Windows local", "Speech was cancelled.")); return; }
            synth ??= new System.Speech.Synthesis.SpeechSynthesizer();
            synth.SetOutputToDefaultAudioDevice();
            EventHandler<System.Speech.Synthesis.SpeakCompletedEventArgs> ended = null;
            ended = (_, e) => { synth.SpeakCompleted -= ended; done.TrySetResult(new(!e.Cancelled && e.Error == null, "Windows local", e.Error == null ? "" : "Windows local speech failed.")); };
            synth.SpeakCompleted += ended;
            token.Register(() => Program.Post(() => { try { synth?.SpeakAsyncCancelAll(); } catch { } done.TrySetResult(new(false, "Windows local", "Speech was cancelled.")); }));
            try { synth.SpeakAsync(text); firstAudio?.Invoke("Windows local"); } catch { synth.SpeakCompleted -= ended; done.TrySetResult(new(false, "Windows local", "Windows local speech failed.")); }
        });
        return done.Task;
    }

    public static bool Shush()
    {
        if (!Speaking) return false;
        Speaking = false;
        try { active?.Cancel(); } catch { }
        try { player?.Dispose(); } catch { }
        player = null;
        try { synth?.SpeakAsyncCancelAll(); } catch { }
        return true;
    }
}

// Gnani is asked for raw 24 kHz PCM. BufferedWaveProvider lets playback begin
// with the first chunk; it never tries to join independent WAV headers.
sealed class RawPcmPlayer : IDisposable
{
    readonly BufferedWaveProvider buffer = new(new WaveFormat(GnaniTtsOptions.SampleRate, 16, 1)) { ReadFully = true, DiscardOnBufferOverflow = true };
    readonly WaveOut output = new();
    bool playing;
    public RawPcmPlayer() => output.Init(buffer);
    public void Add(byte[] pcm) { if (pcm.Length == 0) return; buffer.AddSamples(pcm, 0, pcm.Length); if (!playing) { playing = true; output.Play(); } }
    public async Task DrainAsync(CancellationToken token)
    {
        while (buffer.BufferedBytes > 0) await Task.Delay(20, token);
        await Task.Delay(130, token);
        output.Stop();
    }
    public void Dispose() { try { output.Stop(); } catch { } output.Dispose(); }
}

// Cues from Windows' own sounds (C:\Windows\Media), at Atticus's volume.
static class Sound
{
    public static string PathOf(string name) => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Windows), "Media", name + ".wav");
    public static void Play(string name, double volume)
    {
        var f = PathOf(name);
        if (!File.Exists(f)) return;
        Task.Run(() =>
        {
            try
            {
                using var r = new AudioFileReader(f) { Volume = (float)Math.Clamp(volume, 0, 1) };
                using var o = new WaveOut();
                o.Init(r); o.Play();
                while (o.PlaybackState == PlaybackState.Playing) Thread.Sleep(30);
            }
            catch { }
        });
    }
    public static void Cue(string k) { var n = Prefs.Str(k); if (n != "None" && n != "") Play(n, Prefs.Num("volume") * 2); }   // soundStart / soundDone / soundStop
    // Keep filenames private to the host boundary. Settings receives explicit
    // display labels instead of serialising a raw Windows Media enumeration.
    public static object[] All() => new[] { "None" }.Concat(Directory.Exists(Path.GetDirectoryName(PathOf("x"))) ?
        Directory.GetFiles(Path.GetDirectoryName(PathOf("x"))!, "*.wav").Select(Path.GetFileNameWithoutExtension).Where(n => !n.StartsWith("Alarm") && !n.StartsWith("Ring")).OrderBy(n => n) : Array.Empty<string>())
        .Select(n => (object)new { value = n, label = n == "None" ? "No sound" : System.Text.RegularExpressions.Regex.Replace(n, "([a-z])([A-Z])", "$1 $2") }).ToArray();
}

// The tray icon: quick actions, today's usage.
sealed class Tray
{
    readonly NotifyIcon icon;
    public Tray()
    {
        var ico = Path.Combine(Paths.App, "ui", "AppIcon.ico");
        icon = new NotifyIcon { Icon = File.Exists(ico) ? new Icon(ico) : SystemIcons.Application, Text = "Silly", Visible = Prefs.Bool("menuIcon") };
        icon.ContextMenuStrip = new ContextMenuStrip
        {
            ShowImageMargin = false,
            ShowCheckMargin = false,
            MinimumSize = new Size(330, 0),
            Renderer = new TrayMenuRenderer()
        };
        icon.ContextMenuStrip.Opening += (_, _) => Build();
        icon.MouseClick += (_, e) => { if (e.Button == MouseButtons.Left) Program.Settings.Open(); };
        Build();
    }
    public bool Visible { set => icon.Visible = value; }
    public void Notify(string text) { icon.Visible = true; icon.ShowBalloonTip(5000, "Silly", text, ToolTipIcon.None); if (!Prefs.Bool("menuIcon")) Task.Delay(8000).ContinueWith(_ => Program.Post(() => icon.Visible = Prefs.Bool("menuIcon"))); }
    void Build()
    {
        var m = icon.ContextMenuStrip; m.Items.Clear();
        var keys = Prefs.Str("hotkeyLabel");
        var hint = $"Hold {keys.Replace("+", " + ")} and talk";
        m.Items.Add(new ToolStripMenuItem(hint) { Enabled = false });
        m.Items.Add("Ask Silly", null, (_, _) => { Program.Box.clickTalk = true; Program.Box.Start(); });
        m.Items.Add(Prefs.Bool("paused") ? "Resume Silly" : "Pause Silly", null, (_, _) => { Program.Settings.Apply("paused", !Prefs.Bool("paused")); Program.Settings.Push(); });
        m.Items.Add(new ToolStripSeparator());
        m.Items.Add(new ToolStripMenuItem(Today()) { Enabled = false });
        m.Items.Add(new ToolStripSeparator());
        m.Items.Add("Settings…", null, (_, _) => Program.Settings.Open());
        m.Items.Add("Setup…", null, (_, _) => Program.Onboarding.Open());
        m.Items.Add(new ToolStripSeparator());
        m.Items.Add("Quit Silly", null, (_, _) => { icon.Visible = false; Application.Exit(); });

        foreach (ToolStripItem item in m.Items)
        {
            if (item is ToolStripMenuItem menu)
                Style(menu);
            else if (item is ToolStripSeparator separator)
                separator.Margin = new Padding(10, 5, 10, 5);
        }
    }
    static void Style(ToolStripMenuItem item)
    {
        item.AutoSize = false;
        item.Size = new Size(330, 34);
        item.Padding = new Padding(13, 0, 13, 0);
        item.ShortcutKeyDisplayString = item.Text == "Ask Silly" ? Prefs.Str("hotkeyLabel").Replace("+", " + ") : "";
    }
    static string Today()
    {
        var day = DateTime.Now.ToString("yyyy-MM-dd");
        int n = 0; double usd = 0;
        try
        {
            foreach (var l in File.ReadLines(Paths.Log))
            {
                try
                {
                    using var d = System.Text.Json.JsonDocument.Parse(l);
                    if (!(d.RootElement.GetProperty("at").GetString() ?? "").StartsWith(day)) continue;
                    n++; if (d.RootElement.TryGetProperty("usd", out var u)) usd += u.GetDouble();
                }
                catch { }
            }
        }
        catch { }
        return $"Today: {n} ask{(n == 1 ? "" : "s")} · " + (usd < 1 ? $"{usd * 100:0.00}¢" : $"${usd:0.00}");
    }
}

sealed class TrayMenuRenderer : ToolStripProfessionalRenderer
{
    sealed class Colors : ProfessionalColorTable
    {
        static readonly Color Background = Color.FromArgb(28, 28, 38);
        static readonly Color Hover = Color.FromArgb(52, 52, 70);
        static readonly Color Border = Color.FromArgb(65, 65, 82);
        public override Color ToolStripDropDownBackground => Background;
        public override Color MenuBorder => Border;
        public override Color MenuItemSelected => Hover;
        public override Color MenuItemSelectedGradientBegin => Hover;
        public override Color MenuItemSelectedGradientEnd => Hover;
        public override Color SeparatorDark => Border;
        public override Color SeparatorLight => Border;
    }
    public TrayMenuRenderer() : base(new Colors()) { RoundedEdges = false; }
    protected override void OnRenderItemText(ToolStripItemTextRenderEventArgs e)
    {
        e.TextColor = e.Item.Enabled ? Color.FromArgb(240, 240, 244) : Color.FromArgb(150, 150, 164);
        base.OnRenderItemText(e);
    }
}
