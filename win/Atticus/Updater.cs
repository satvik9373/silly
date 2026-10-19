// Updates: build.ps1 records the source folder (a git clone). Atticus pulls and builds from it into a folder beside
// itself (Atticus.next), then swaps it in when it restarts while you're not using it. Local edits or a failed build
// leave the running version alone.
using System.Diagnostics;

namespace Atticus;

static class Updater
{
    public static string Status = "";
    static readonly string App = Paths.App, Next = Paths.App + ".next";
    static bool checking;

    // Staging an update and replacing a running application are separate
    // decisions. A manual check may prepare an update, but it must not restart
    // Silly unless the user has explicitly enabled automatic updates.
    internal static bool ShouldActivateStagedUpdate(bool automaticUpdatesEnabled) => automaticUpdatesEnabled;
    internal static string StagedStatus(bool automaticUpdatesEnabled) => automaticUpdatesEnabled
        ? "Update ready. Restarting when you’re not using it…"
        : "Update ready. Enable automatic updates or restart after reviewing it.";

    static (int code, string output) Ps(string script, int secs)
    {
        try
        {
            var si = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true, WorkingDirectory = Paths.Install("source") };
            ChildEnvironment.RemoveSecrets(si);
            foreach (var a in new[] { "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script }) si.ArgumentList.Add(a);
            using var p = Process.Start(si)!;
            var o = p.StandardOutput.ReadToEndAsync(); var e = p.StandardError.ReadToEndAsync();
            if (!p.WaitForExit(secs * 1000)) { try { p.Kill(true); } catch { } return (-1, "timed out"); }
            return (p.ExitCode, o.Result + e.Result);
        }
        catch (Exception ex) { return (-1, ex.Message); }
    }

    public static void Check(Action done)
    {
        if (checking) return;
        checking = true; Status = "Checking…"; done();
        Task.Run(() =>
        {
            var src = Paths.Install("source");
            var (code, output) = src == "" || !Directory.Exists(Path.Combine(src, ".git")) ? (3, "") : Ps(@"
                if (git status --porcelain) { exit 5 }
                git fetch -q 2>$null; if ($LASTEXITCODE) { exit 4 }
                if ((git rev-parse HEAD) -eq (git rev-parse '@{u}')) { exit 0 }
                git pull -q --ff-only 2>$null; if ($LASTEXITCODE) { exit 5 }
                & powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -Stage *> $null; if ($LASTEXITCODE) { exit 6 }
                exit 10", 900);
            if (code is not (0 or 10)) Program.Err($"update check {code}: {output.Trim()}");
            Program.Post(() =>
            {
                checking = false;
                Status = code switch
                {
                    0 => "Up to date", 3 => "Source folder not found (run install.ps1 again)", 4 => "Couldn’t reach GitHub",
                    5 => "Skipped: the source folder has local changes", 6 => "Update downloaded, but the build failed",
                    10 => StagedStatus(Prefs.Bool("autoUpdate")), _ => "Update failed"
                };
                done();
                if (code == 10 && ShouldActivateStagedUpdate(Prefs.Bool("autoUpdate"))) RestartWhenIdle();
            });
        });
    }

    public static bool Pending => Directory.Exists(Next) && File.Exists(Path.Combine(Next, "Silly.exe"));

    public static void RestartWhenIdle()
    {
        var b = Program.Box;
        if (b.busy || b.Listening || Voice.Speaking || Program.Settings.ContainsFocus || Program.Onboarding.Visible || b.Visible && b.Opacity > 0)
        {
            var t = new System.Windows.Forms.Timer { Interval = 30000 };
            t.Tick += (_, _) => { t.Dispose(); RestartWhenIdle(); };
            t.Start();
            return;
        }
        Swap();
    }

    // A small PowerShell outside the app: wait for this process to end, put Atticus.next in place, start it.
    // Anything locked: the old version starts again and the swap is tried at the next restart.
    static void Swap()
    {
        var script = $@"
            $app = '{App.Replace("'", "''")}'; $next = $app + '.next'; $old = $app + '.old'
            Wait-Process -Id {Environment.ProcessId} -Timeout 20 -ErrorAction SilentlyContinue
            Start-Sleep -Milliseconds 800
            Remove-Item $old -Recurse -Force -ErrorAction SilentlyContinue
            $ok = $false
            for ($i = 0; $i -lt 10 -and -not $ok; $i++) {{
              try {{ Move-Item $app $old -ErrorAction Stop; $ok = $true }} catch {{ Start-Sleep -Milliseconds 500 }}
            }}
            if ($ok) {{
              try {{ Move-Item $next $app -ErrorAction Stop }} catch {{ Move-Item $old $app }}
            }}
            Start-Process (Join-Path $app 'Silly.exe')
            Remove-Item $old -Recurse -Force -ErrorAction SilentlyContinue";
        var si = new ProcessStartInfo("powershell.exe") { UseShellExecute = false, CreateNoWindow = true };
        ChildEnvironment.RemoveSecrets(si);
        foreach (var a in new[] { "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-Command", script }) si.ArgumentList.Add(a);
        Process.Start(si);
        Application.Exit();
    }

    public static void Schedule()   // opt-in: a minute after launch, then every 6 hours
    {
        // A staged update was created only by an explicit Check now action, but
        // it must still wait for the user to opt into automatic updates before
        // changing a running application on a later launch.
        if (Pending && Prefs.Bool("autoUpdate")) { RestartWhenIdle(); return; }
        if (Pending) { Status = StagedStatus(false); return; }
        if (!Prefs.Bool("autoUpdate")) return;
        var first = new System.Windows.Forms.Timer { Interval = 60_000 };
        first.Tick += (_, _) => { first.Dispose(); if (Prefs.Bool("autoUpdate")) Check(() => Program.Settings.Push()); };
        first.Start();
        var every = new System.Windows.Forms.Timer { Interval = 6 * 3600_000 };
        every.Tick += (_, _) => { if (Prefs.Bool("autoUpdate")) Check(() => Program.Settings.Push()); };
        every.Start();
    }
}
