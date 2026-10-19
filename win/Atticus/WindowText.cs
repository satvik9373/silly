// `Atticus.exe --text <app> [title words]` (atticus.py --watch): the text in that app's window, read on this PC with Windows' own
// OCR, even when the window is covered (not minimized). Exit 1 when no window could be read.
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.WindowsRuntime;
using System.Text;
using Windows.Graphics.Imaging;
using Windows.Media.Ocr;
using Windows.Storage.Streams;

namespace Atticus;

static class WindowText
{
    [DllImport("user32")] static extern bool EnumWindows(EnumProc fn, IntPtr l);
    delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32")] static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32")] static extern bool IsIconic(IntPtr h);
    [DllImport("user32", CharSet = CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32")] static extern bool GetWindowRect(IntPtr h, out Native.RECT r);
    [DllImport("user32")] static extern bool PrintWindow(IntPtr h, IntPtr dc, uint flags);

    static string Key(string s) => new string(s.ToLowerInvariant().Replace(".exe", "").Where(char.IsLetterOrDigit).ToArray());

    public static int Run(string app, string words)
    {
        words = words.ToLowerInvariant();
        var found = new List<(IntPtr h, string title, int area)>();
        EnumWindows((h, _) =>
        {
            if (!IsWindowVisible(h) || IsIconic(h)) return true;
            var sb = new StringBuilder(512); GetWindowText(h, sb, 512);
            var title = sb.ToString();
            if (title == "" || (words != "" && !title.ToLowerInvariant().Contains(words))) return true;
            GetWindowRect(h, out var r);
            int w = r.Right - r.Left, ht = r.Bottom - r.Top;
            if (w < 200 || ht < 150) return true;
            var name = Native.ProcessName(h);
            Native.GetWindowThreadProcessId(h, out var pid);
            string proc = ""; try { using var p = System.Diagnostics.Process.GetProcessById((int)pid); proc = p.ProcessName; } catch { }
            var k = Key(app);
            if (k == Key(name) || k == Key(proc) || k == Key(title.Split(" - ").Last())) found.Add((h, title, w * ht));
            return true;
        }, IntPtr.Zero);
        var engine = OcrEngine.TryCreateFromUserProfileLanguages();
        if (engine == null) return 1;
        foreach (var (h, _, _) in found.OrderByDescending(f => f.area).Take(4))   // real windows first (biggest); next one if a capture reads nothing
        {
            var text = Read(h, engine);
            if (string.IsNullOrWhiteSpace(text)) continue;
            Console.OutputEncoding = Encoding.UTF8;
            Console.Write(text);
            return 0;
        }
        return 1;
    }

    static string Read(IntPtr h, OcrEngine engine)
    {
        try
        {
            GetWindowRect(h, out var r);
            int w = r.Right - r.Left, ht = r.Bottom - r.Top;
            using var bmp = new Bitmap(w, ht, System.Drawing.Imaging.PixelFormat.Format32bppArgb);
            using (var g = Graphics.FromImage(bmp))
            {
                var dc = g.GetHdc();
                PrintWindow(h, dc, 2);   // PW_RENDERFULLCONTENT: browsers and other GPU-drawn windows too
                g.ReleaseHdc(dc);
            }
            using var ms = new MemoryStream();
            bmp.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
            using var ras = new InMemoryRandomAccessStream();
            ras.WriteAsync(ms.ToArray().AsBuffer()).AsTask().Wait();
            ras.Seek(0);
            var dec = BitmapDecoder.CreateAsync(ras).AsTask().Result;
            using var sb = dec.GetSoftwareBitmapAsync(BitmapPixelFormat.Bgra8, BitmapAlphaMode.Premultiplied).AsTask().Result;
            var res = engine.RecognizeAsync(sb).AsTask().Result;
            return string.Join("\n", res.Lines.Select(l => l.Text));
        }
        catch { return ""; }
    }
}
