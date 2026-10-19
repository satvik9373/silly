// The pages in ui\ were written for macOS's WKWebView: they post to window.webkit.messageHandlers.<name>. A small script
// injected before each page maps that onto WebView2's chrome.webview.postMessage, so the same pages run here unchanged.
using System.Text.Json;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace Atticus;

static class Web
{
    const string Shim = "window.webkit = { messageHandlers: new Proxy({}, { get: (_, n) => ({ postMessage: b => chrome.webview.postMessage({ n, b }) }) }) };" +
                        "window.sillyPlatform = 'win';" +
                        "if (document.documentElement) document.documentElement.setAttribute('data-webawesome', 'https://ui.silly.local/vendor/webawesome');";
    static Task<CoreWebView2Environment> env;
    static Task<CoreWebView2Environment> Env => env ??= CoreWebView2Environment.CreateAsync(null, Path.Combine(Paths.Local, "WebView2"));

    // A page from ui\ (orbs.js goes in place of its /*ORBS*/ marker); onMessage(handler name, body) on the UI thread.
    public static async Task<WebView2> Load(Control host, string page, Action<string, JsonElement> onMessage, bool transparent, string extra = "")
    {
        var v = new WebView2 { Dock = DockStyle.Fill };
        if (transparent) v.DefaultBackgroundColor = Color.Transparent;
        host.Controls.Add(v);
        await v.EnsureCoreWebView2Async(await Env);
        // Settings, onboarding and the overlay are local application assets.
        // Serving them from a virtual host gives module scripts, component
        // styles and local fonts a stable same-origin URL without a CDN.
        v.CoreWebView2.SetVirtualHostNameToFolderMapping("ui.silly.local", Path.Combine(Paths.App, "ui"), CoreWebView2HostResourceAccessKind.Allow);
        var s = v.CoreWebView2.Settings;
        s.AreDevToolsEnabled = Environment.GetEnvironmentVariable("SILLY_DEVTOOLS") == "1";
        s.AreDefaultContextMenusEnabled = false; s.IsZoomControlEnabled = false; s.IsStatusBarEnabled = false; s.AreBrowserAcceleratorKeysEnabled = false;
        if (Environment.GetEnvironmentVariable("SILLY_WEB_DIAGNOSTICS") == "1")
        {
            v.CoreWebView2.WebResourceResponseReceived += (_, e) =>
            {
                if (e.Response.StatusCode >= 400) Console.Error.WriteLine($"web resource {e.Response.StatusCode}: {e.Request.Uri}");
            };
            v.CoreWebView2.ProcessFailed += (_, e) => Console.Error.WriteLine($"web process failed: {e.ProcessFailedKind}");
        }
        await v.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(Shim + extra);
        v.CoreWebView2.WebMessageReceived += (_, e) =>
        {
            try
            {
                using var d = JsonDocument.Parse(e.WebMessageAsJson);
                onMessage(d.RootElement.GetProperty("n").GetString(), d.RootElement.GetProperty("b").Clone());
            }
            catch { }
        };
        v.CoreWebView2.NewWindowRequested += (_, e) => { e.Handled = true; Open(e.Uri); };   // links open in the user's browser
        string html;
        try { html = File.ReadAllText(Paths.Ui(page)); } catch { html = $"missing {page}"; }
        if (html.Contains("/*ORBS*/"))
            html = html.Replace("/*ORBS*/", File.Exists(Paths.Ui("orbs.js")) ? File.ReadAllText(Paths.Ui("orbs.js")) : "");
        html = html.Replace("<head>", "<head><base href=\"https://ui.silly.local/\">");
        html = html.Replace("src=\"vendor/webawesome/webawesome.loader.js\"",
            "src=\"https://ui.silly.local/vendor/webawesome/webawesome.loader.js\"");
        v.CoreWebView2.NavigateToString(html);
        return v;
    }

    public static void Js(WebView2 v, string call)
    {
        if (v?.CoreWebView2 == null) return;
        try { _ = v.CoreWebView2.ExecuteScriptAsync(call); } catch { }
    }

    public static string Json(object o) => JsonSerializer.Serialize(o);

    public static void Open(string target)
    {
        try { System.Diagnostics.Process.Start(new System.Diagnostics.ProcessStartInfo(target) { UseShellExecute = true }); } catch { }
    }
}

// "Show me where": a soft pulsing ring at a spot on screen for a few seconds. "@ x y" in screen pixels.
sealed class Ring : Form
{
    static Ring now;
    readonly System.Windows.Forms.Timer t = new() { Interval = 30 };
    int tick;
    Ring(int x, int y)
    {
        FormBorderStyle = FormBorderStyle.None; ShowInTaskbar = false; TopMost = true; BackColor = Color.Magenta; TransparencyKey = Color.Magenta;
        StartPosition = FormStartPosition.Manual; Bounds = new Rectangle(x - 40, y - 40, 80, 80);
        DoubleBuffered = true;
        t.Tick += (_, _) => { if (++tick > 200) Close(); Invalidate(); };
        t.Start();
    }
    protected override bool ShowWithoutActivation => true;
    protected override CreateParams CreateParams { get { var c = base.CreateParams; c.ExStyle |= Native.WS_EX_TOOLWINDOW | Native.WS_EX_NOACTIVATE | Native.WS_EX_TRANSPARENT | Native.WS_EX_LAYERED; return c; } }
    protected override void OnPaint(PaintEventArgs e)
    {
        var s = 0.75f + 0.25f * MathF.Abs(MathF.Sin(tick / 10f));
        var r = 32 * s;
        e.Graphics.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
        using var pen = new Pen(Color.FromArgb(10, 132, 255), 4);
        e.Graphics.DrawEllipse(pen, 40 - r, 40 - r, 2 * r, 2 * r);
    }
    protected override void OnFormClosed(FormClosedEventArgs e) { t.Dispose(); if (now == this) now = null; base.OnFormClosed(e); }
    public static void At(string line)
    {
        var p = line.Split(' ').Skip(1).Select(s => int.TryParse(s, out var n) ? n : int.MinValue).ToArray();
        if (p.Length != 2 || p.Contains(int.MinValue)) return;
        now?.Close();
        now = new Ring(p[0], p[1]); now.Show();
    }
}
