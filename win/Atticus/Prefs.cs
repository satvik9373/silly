// Settings, shared with atticus.py (model, screen, openOn, instant…): %APPDATA%\Atticus\settings.json.
// Where things live: the app folder (atticus.py, ui\), the Python that runs it, the speech model.
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Atticus;

static class Paths
{
    public const string Product = "Silly";
    public static readonly string Config = Environment.GetEnvironmentVariable("SILLY_DIR") is { Length: > 0 } d ? d
        : Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), Product);
    public static readonly string Local = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), Product);
    public static readonly string App = AppContext.BaseDirectory.TrimEnd('\\');   // build.ps1 copies atticus.py and ui\ next to Atticus.exe
    public static string Ui(string f) => Path.Combine(App, "ui", f);
    public static readonly string Recent = Path.Combine(Config, "recent.jsonl");
    public static readonly string Log = Path.Combine(Config, "log.jsonl");
    static JsonObject install;
    // atticus.json next to the exe (written by build.ps1): {"python": "...", "source": "<git clone>"}
    public static string Install(string k)
    {
        try { install ??= JsonNode.Parse(File.ReadAllText(Path.Combine(App, "silly.json")))!.AsObject(); } catch { install = new JsonObject(); }
        return install[k]?.GetValue<string>() ?? "";
    }
    public static string Python => Environment.GetEnvironmentVariable("SILLY_PYTHON") is { Length: > 0 } dev && File.Exists(dev) ? dev
        : Install("python") is { Length: > 0 } p && File.Exists(p) ? p : Path.Combine(Local, "venv", "Scripts", "python.exe");
    public static string Script => Environment.GetEnvironmentVariable("SILLY_SCRIPT") is { Length: > 0 } dev && File.Exists(dev) ? dev
        : File.Exists(Path.Combine(App, "silly.py")) ? Path.Combine(App, "silly.py") : Path.Combine(Install("source"), "atticus.py");
    public static string Model => Path.Combine(Local, "models", "ggml-" + Prefs.Str("speechModel") + ".bin");
}

static class Prefs
{
    public static string File => Path.Combine(Paths.Config, "settings.json");
    // Hotkey: virtual-key code + modifiers (1 Alt, 2 Ctrl, 4 Shift, 8 Win, like RegisterHotKey).
    public static readonly Dictionary<string, object> Defaults = new()
    {
        ["hotkeyCode"] = 0x20, ["hotkeyMods"] = 3, ["hotkeyLabel"] = "Ctrl+Alt+Space", ["login"] = true, ["paused"] = false, ["corner"] = "top-left", ["linger"] = "normal",
        ["soundStart"] = "Speech On", ["soundDone"] = "Windows Notify System Generic", ["soundStop"] = "Speech Off", ["volume"] = 0.3, ["model"] = "haiku", ["aiPrimary"] = "claude-code", ["aiBackup1"] = "none", ["aiBackup2"] = "none", ["aiFailover"] = true, ["aiFreeOnly"] = true, ["aiClaudeSubscriptionNoCharge"] = false, ["aiOpenAIModel"] = "", ["instant"] = true,
        ["ahead"] = true, ["aheadDelay"] = 0.9, ["live"] = true, ["screen"] = "auto", ["openOn"] = "here",
        ["speak"] = true, ["autoCopy"] = false, ["hideWhenSharing"] = true, ["menuIcon"] = true, ["autoUpdate"] = false,
        ["learn"] = true, ["safe"] = true, ["pointer"] = false, ["learnMe"] = true, ["stats"] = true, ["tips"] = true, ["askMe"] = true, ["escalate"] = true, ["escalateAuto"] = false, ["input"] = "voice", ["talkMode"] = "hold",
        ["boxW"] = 460, ["boxH"] = 360, ["speechModel"] = "base.en", ["speechProvider"] = "local", ["cloudFallback"] = "local", ["gnaniLanguage"] = "en-IN", ["gnaniMinSilence"] = 350, ["gnaniVocabulary"] = "", ["gnaniVocabularyStrength"] = "1.0",
        ["ttsProvider"] = "windows", ["ttsFallback"] = true, ["speechReplyMode"] = "brief", ["gnaniTtsModel"] = "timbre-v3.0", ["gnaniTtsVoice"] = "Shivani", ["gnaniTtsLanguage"] = "en-IN", ["gnaniTtsSpeed"] = 1.0, ["ttsTimeout"] = 15, ["onboarded"] = false,
    };
    public static Dictionary<string, object> D = Load();

    static Dictionary<string, object> Load()
    {
        var d = new Dictionary<string, object>(Defaults);
        try
        {
            foreach (var (k, v) in JsonNode.Parse(System.IO.File.ReadAllText(File))!.AsObject())
                d[k] = v?.GetValueKind() switch
                {
                    JsonValueKind.True => true, JsonValueKind.False => false, JsonValueKind.Number => v.GetValue<double>(),
                    JsonValueKind.String => v.GetValue<string>(), _ => d.GetValueOrDefault(k)
                };
        }
        catch { }
        // A prior static UI could persist a voice from the other Gnani model.
        // Heal it once at load so every subsequent turn has a valid pair.
        var model = d.GetValueOrDefault("gnaniTtsModel") as string;
        if (!GnaniVoiceCatalog.IsKnownModel(model)) model = "timbre-v3.0";
        d["gnaniTtsModel"] = model;
        var voice = d.GetValueOrDefault("gnaniTtsVoice") as string;
        if (!GnaniVoiceCatalog.IsVoiceForModel(model, voice)) d["gnaniTtsVoice"] = GnaniVoiceCatalog.DefaultVoice(model, d.GetValueOrDefault("gnaniTtsLanguage") as string ?? "en-IN");
        return d;
    }

    public static void Set(string k, object v)
    {
        D[k] = v;
        Directory.CreateDirectory(Paths.Config);
        var tmp = File + ".tmp";
        System.IO.File.WriteAllText(tmp, JsonSerializer.Serialize(new SortedDictionary<string, object>(D), new JsonSerializerOptions { WriteIndented = true }));
        System.IO.File.Move(tmp, File, true);
    }
    public static bool Bool(string k) => D.GetValueOrDefault(k) is bool b && b;
    public static string Str(string k) => D.GetValueOrDefault(k) as string ?? "";
    public static double Num(string k) => D.GetValueOrDefault(k) switch { double x => x, int i => i, _ => 0 };
}

// atticus.py, run with Atticus's own Python, inside Atticus's job object. Output is UTF-8 lines.
static class Py
{
    public static Process Start(IEnumerable<string> args, Dictionary<string, string> env = null, bool input = false)
    {
        var si = new ProcessStartInfo(Paths.Python) { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true,
            RedirectStandardInput = input, StandardOutputEncoding = Encoding.UTF8, StandardErrorEncoding = Encoding.UTF8, WorkingDirectory = Path.GetTempPath() };
        if (input) si.StandardInputEncoding = new UTF8Encoding(false);
        si.ArgumentList.Add("-X"); si.ArgumentList.Add("utf8");
        si.ArgumentList.Add(Paths.Script);
        foreach (var a in args) si.ArgumentList.Add(a);
        si.Environment["PYTHONUTF8"] = "1";
        si.Environment["PYTHONIOENCODING"] = "utf-8";
        si.Environment["SILLY_APP"] = Environment.ProcessPath;
        if (env != null) foreach (var (k, v) in env) si.Environment[k] = v;
        ChildEnvironment.RemoveSecrets(si);
        var p = Process.Start(si)!;
        try { Native.AssignProcessToJobObject(Native.Job, p.Handle); } catch { }
        return p;
    }

    // Run and wait (helpers like --state, --check): stdout, or "" after `secs`.
    public static string Run(IEnumerable<string> args, int secs = 30)
    {
        try
        {
            using var p = Start(args);
            var err = p.StandardError.ReadToEndAsync();
            var t = p.StandardOutput.ReadToEndAsync();
            if (!p.WaitForExit(secs * 1000)) { try { p.Kill(true); } catch { } return ""; }
            return t.Result;
        }
        catch { return ""; }
    }

    // Run with lines on stdin (secrets never go in a command line), wait: stdout.
    public static string RunWithInput(IEnumerable<string> args, string input, int secs = 30)
    {
        try
        {
            using var p = Start(args, input: true);
            p.StandardInput.Write(input); p.StandardInput.Close();
            var err = p.StandardError.ReadToEndAsync();
            var t = p.StandardOutput.ReadToEndAsync();
            if (!p.WaitForExit(secs * 1000)) { try { p.Kill(true); } catch { } return "timed out"; }
            return t.Result.Trim();
        }
        catch (Exception e) { return e.Message; }
    }

    public static void Stop(Process p)
    {
        if (p == null) return;
        try { if (!p.HasExited) p.Kill(true); } catch { }
    }
}

// Speech credentials belong only to the native Gnani transport. Any process
// that Silly starts for helpers, updates, or optional setup inherits this
// filtered environment rather than the host's development-key environment.
static class ChildEnvironment
{
    public static void RemoveSecrets(ProcessStartInfo startInfo) => startInfo.Environment.Remove("GNANI_API_KEY");
}
