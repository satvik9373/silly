using System.Net.WebSockets;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.Json;
using System.Threading.Channels;

namespace Atticus;

// Gnani's published catalog as of 2026-10-17. Update this single list from
// https://docs.gnani.ai/api/TTS/available-voices when Gnani changes it.
static class GnaniVoiceCatalog
{
    static readonly Dictionary<string, string[]> Voices = new()
    {
        ["timbre-v2.5"] = "Ambuja,Asmita,Bhavna,Brinda,Chitra,Deepak,Devika,Dhruva,Falak,Girish,Hemraj,Ishaan,Jalaj,Jwala,Kaveri,Kavin,Kirra,Lavanya,Lehara,Mehuli,Nalini,Noopur,Omkar,Poorvi,Pranav,Reshma,Riyaan,Roopesh,Saanvi,Shlok,Suhana,Trisha,Trupti,Urmila,Varuni,Vedika,Veera,Vikrant,Yashvi,Yukti,Zahira,Zayan".Split(','),
        ["timbre-v3.0"] = "Shivani,Lakshmi,Kalpana,Chetana,Vasudha,Riyaa,Tarika,Avinash,Shubham,Prakash,Devansh,Yashraj,Harshad".Split(','),
    };
    static readonly HashSet<string> Languages = new() { "auto", "en-IN", "hi-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "bn-IN", "gu-IN", "hi-en" };
    public static bool IsKnownModel(string model) => Voices.ContainsKey(model ?? "");
    public static bool IsKnownLanguage(string language) => Languages.Contains(language ?? "");
    public static bool IsVoiceForModel(string model, string voice) => Voices.TryGetValue(model ?? "", out var voices) && voices.Contains(voice ?? "", StringComparer.Ordinal);
    public static string DefaultVoice(string model, string language) =>
        model == "timbre-v2.5" && language == "hi-IN" ? "Nalini" :
        model == "timbre-v2.5" && language == "hi-en" ? "Poorvi" :
        model == "timbre-v2.5" ? "Kaveri" : "Shivani";
    public static Dictionary<string, object[]> ForUi() => Voices.ToDictionary(p => p.Key,
        p => p.Value.Select(v => (object)new { value = v, label = v }).ToArray());
}

// Credentials are deliberately not a preference.  Development can use the
// process-only GNANI_API_KEY; normal use reads the current user's Windows
// Credential Manager entry instead.
static class GnaniCredentials
{
    const string Target = "Silly/GnaniApiKey";
    const int Generic = 1, PersistLocalMachine = 2;
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)] struct Credential
    {
        public int Flags, Type; public string TargetName, Comment; public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public int CredentialBlobSize; public IntPtr CredentialBlob; public int Persist, AttributeCount; public IntPtr Attributes; public string TargetAlias, UserName;
    }
    [DllImport("Advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern bool CredRead(string target, int type, int flags, out IntPtr credential);
    [DllImport("Advapi32.dll", SetLastError = true)] static extern void CredFree(IntPtr buffer);
    [DllImport("Advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern bool CredWrite(ref Credential credential, int flags);
    [DllImport("Advapi32.dll", CharSet = CharSet.Unicode, SetLastError = true)] static extern bool CredDelete(string target, int type, int flags);

    public static bool TryGet(out string apiKey, out string error)
    {
        apiKey = Environment.GetEnvironmentVariable("GNANI_API_KEY")?.Trim() ?? "";
        if (apiKey.Length > 0) { error = ""; return true; }
        try
        {
            if (CredRead(Target, Generic, 0, out var ptr))
            {
                try
                {
                    var c = Marshal.PtrToStructure<Credential>(ptr);
                    apiKey = c.CredentialBlobSize == 0 ? "" : Marshal.PtrToStringUni(c.CredentialBlob, c.CredentialBlobSize / 2)?.Trim() ?? "";
                }
                finally { CredFree(ptr); }
            }
        }
        catch { }
        error = apiKey.Length == 0 ? "Gnani needs an API key. Save one in Silly Settings or select Windows local speech." : "";
        return apiKey.Length > 0;
    }

    // Called only from the Settings password field; the value is never written
    // to settings.json, command lines, diagnostics, or a log.
    public static bool Save(string apiKey, out string error)
    {
        error = ""; apiKey = apiKey?.Trim() ?? "";
        try
        {
            if (apiKey.Length == 0) { CredDelete(Target, Generic, 0); return true; }
            var bytes = Encoding.Unicode.GetBytes(apiKey);
            var blob = Marshal.AllocCoTaskMem(bytes.Length);
            try
            {
                Marshal.Copy(bytes, 0, blob, bytes.Length);
                var c = new Credential { Type = Generic, TargetName = Target, UserName = "Silly", Persist = PersistLocalMachine, CredentialBlobSize = bytes.Length, CredentialBlob = blob };
                if (!CredWrite(ref c, 0)) { error = "Windows Credential Manager could not save the Gnani key."; return false; }
                return true;
            }
            finally { Marshal.Copy(new byte[bytes.Length], 0, blob, bytes.Length); Marshal.FreeCoTaskMem(blob); }
        }
        catch { error = "Windows Credential Manager could not save the Gnani key."; return false; }
    }
}

// Gnani transport primitives never persist credentials in Silly settings or logs.
// Development can use GNANI_API_KEY; user-entered keys live in Credential Manager.
static class GnaniErrors
{
    static bool Has(string text, params string[] terms) => terms.Any(term => text.Contains(term, StringComparison.OrdinalIgnoreCase));
    public static string SttServer(string message)
    {
        var text = message ?? "";
        if (Has(text, "quota", "credit", "exhaust", "rate limit", "429")) return "Gnani cloud speech quota is exhausted. Check your Gnani account or select Local Whisper.";
        if (Has(text, "api key", "auth", "unauthor", "forbidden", "401", "403", "credential")) return "Gnani cloud speech rejected the saved key. Check it in Settings or select Local Whisper.";
        if (Has(text, "timeout", "timed out")) return "Gnani cloud speech timed out. Try again or select Local Whisper.";
        return "Gnani cloud speech rejected the request. Check the connection and speech settings.";
    }
    public static string TtsServer(string message)
    {
        var text = message ?? "";
        if (Has(text, "quota", "credit", "exhaust", "rate limit", "429")) return "Gnani speech output quota is exhausted. Check your Gnani account or use Windows local speech.";
        if (Has(text, "api key", "auth", "unauthor", "forbidden", "401", "403", "credential")) return "Gnani speech output rejected the saved key. Check it in Settings or use Windows local speech.";
        if (Has(text, "timeout", "timed out")) return "Gnani speech output timed out. Try Windows local speech.";
        return "Gnani speech output rejected the request. Check the connection and voice settings.";
    }
    public static string SttTransport(string message)
    {
        var text = message ?? "";
        if (Has(text, "quota", "credit", "exhaust", "rate limit", "429", "api key", "auth", "unauthor", "forbidden", "401", "403", "credential")) return SttServer(text);
        return "Could not connect to Gnani cloud speech. Check your connection, API key, or quota.";
    }
    public static string TtsTransport(string message)
    {
        var text = message ?? "";
        if (Has(text, "quota", "credit", "exhaust", "rate limit", "429", "api key", "auth", "unauthor", "forbidden", "401", "403", "credential")) return TtsServer(text);
        return "Could not connect to Gnani speech output. Check the connection, key, or quota.";
    }
}

sealed record GnaniSttOptions(string ApiKey, string Language, int MinSilence = 350, string Vocabulary = "", string VocabularyStrength = "")
{
    public const int SampleRate = 16000, FrameBytes = 1024, FrameMilliseconds = 32;
    public const int ShortCommandMinSpeechMilliseconds = 100, ShortCommandMinSegmentMilliseconds = 100;
    static readonly HashSet<string> Languages = new() { "en-IN", "hi-IN", "kn-IN", "ta-IN", "te-IN", "ml-IN", "mr-IN", "pa-IN", "bn-IN", "gu-IN" };
    public static bool IsSupportedLanguage(string language) => Languages.Contains(language ?? "");
    public static int SilenceFramesFor(int milliseconds) => (int)Math.Ceiling(milliseconds / (double)FrameMilliseconds) + 1;
    public static bool TryFromEnvironment(out GnaniSttOptions options, out string error)
    {
        GnaniCredentials.TryGet(out var key, out _);
        var configuredLanguage = Prefs.Str("gnaniLanguage");
        if (!TryCreate(key, configuredLanguage, out options, out error)) return false;
        if (!TryVocabulary(Prefs.Str("gnaniVocabulary"), Prefs.Str("gnaniVocabularyStrength"), out var words, out var strength, out error)) { options = null; return false; }
        var silence = (int)Prefs.Num("gnaniMinSilence");
        if (silence == 0) int.TryParse(Prefs.Str("gnaniMinSilence"), out silence);
        if (silence is < 100 or > 2000) silence = 350;
        options = options with { MinSilence = silence, Vocabulary = words, VocabularyStrength = strength };
        return true;
    }

    // Kept separate from environment access so protocol tests can verify absent
    // credentials without reading or exposing a developer's real secret.
    public static bool TryCreate(string apiKey, string language, out GnaniSttOptions options, out string error)
    {
        var key = apiKey?.Trim();
        if (string.IsNullOrEmpty(key)) { options = null; error = "Gnani cloud speech needs a key. Select Local Whisper or save a Gnani key in Settings."; return false; }
        language = string.IsNullOrWhiteSpace(language) ? "en-IN" : language.Trim();
        if (!IsSupportedLanguage(language)) { options = null; error = "Gnani transcription language is invalid. Choose one of Gnani's supported language codes."; return false; }
        options = new GnaniSttOptions(key, language);
        error = ""; return true;
    }

    // Gnani word boosting accepts at most 100 single words made of letters.
    // This is intentionally not a phrase substitution feature.
    public static bool TryVocabulary(string raw, string strength, out string words, out string score, out string error)
    {
        var list = (raw ?? "").Split(new[] { ',', '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries).Select(x => x.Trim()).Where(x => x.Length > 0).Distinct(StringComparer.OrdinalIgnoreCase).ToArray();
        score = string.IsNullOrWhiteSpace(strength) ? "1.0" : strength.Trim();
        if (list.Length > 100 || list.Any(x => !System.Text.RegularExpressions.Regex.IsMatch(x, @"^\p{L}+$")) || (list.Length > 0 && score is not ("0.5" or "1.0" or "1.5" or "2.0")))
        { words = ""; error = "Gnani vocabulary uses up to 100 single words containing letters only and a strength of 0.5, 1.0, 1.5, or 2.0."; return false; }
        words = list.Length == 0 ? "" : JsonSerializer.Serialize(list); error = ""; return true;
    }

    public IReadOnlyDictionary<string, string> Headers()
    {
        var headers = new Dictionary<string, string> {
            ["x-api-key-id"] = ApiKey,
            ["lang_code"] = Language,
            ["x-sample-rate"] = SampleRate.ToString(),
            ["x-format"] = "verbatim",
            ["x-min-silence-ms"] = MinSilence.ToString(),
            // Gnani documents these values as appropriate for short commands;
            // they still reject click/noise while allowing brief yes/no replies.
            ["x-min-speech-ms"] = ShortCommandMinSpeechMilliseconds.ToString(),
            ["x-min-segment-ms"] = ShortCommandMinSegmentMilliseconds.ToString(),
        };
        if (Vocabulary.Length > 0) { headers["x-bias-list"] = Vocabulary; headers["x-bias-score"] = VocabularyStrength; }
        return headers;
    }
}

sealed class GnaniPcmFramer
{
    readonly List<byte> pending = new();
    public IEnumerable<byte[]> Add(byte[] pcm)
    {
        pending.AddRange(pcm);
        while (pending.Count >= GnaniSttOptions.FrameBytes)
        {
            var frame = pending.Take(GnaniSttOptions.FrameBytes).ToArray();
            pending.RemoveRange(0, GnaniSttOptions.FrameBytes);
            yield return frame;
        }
    }

    // The provider accepts only full frames. At end-of-turn retain the final
    // few milliseconds rather than dropping them; zero padding is PCM silence.
    public byte[] Flush()
    {
        if (pending.Count == 0) return Array.Empty<byte>();
        var frame = new byte[GnaniSttOptions.FrameBytes];
        pending.CopyTo(frame, 0); pending.Clear();
        return frame;
    }
}

sealed class GnaniTranscriptAccumulator
{
    readonly SortedDictionary<int, string> segments = new();
    // Realtime services can revise an interim segment using the same ID. Keep
    // the last value per segment instead of treating every repeated ID as an
    // immutable duplicate. Identical retransmissions remain ignored.
    readonly Dictionary<string, (int Index, string Text)> received = new(StringComparer.Ordinal);
    public string Text => string.Join(" ", segments.Values.Where(t => !string.IsNullOrWhiteSpace(t))).Trim();

    public bool AddServerMessage(string json, out string transcript, out string error)
    {
        transcript = ""; error = "";
        try
        {
            using var doc = JsonDocument.Parse(json); var root = doc.RootElement;
            var type = root.TryGetProperty("type", out var typeEl) ? typeEl.GetString() : "";
            if (type == "error") { error = GnaniErrors.SttServer(root.TryGetProperty("message", out var msg) ? msg.GetString() : null); return false; }
            if (type != "transcript") return false;
            var id = root.TryGetProperty("segment_id", out var idEl) ? idEl.GetString() ?? "" : "";
            var index = segments.Count;
            var indexed = false;
            if (root.TryGetProperty("segment_index", out var ixEl) && ixEl.TryGetInt32(out var suppliedIndex))
            {
                index = suppliedIndex;
                indexed = true;
            }
            var key = id.Length > 0 ? "id:" + id : indexed ? "index:" + index : "text:" + (root.TryGetProperty("text", out var fingerprint) ? fingerprint.GetString() ?? "" : "");
            if (!indexed && received.TryGetValue(key, out var priorSegment)) index = priorSegment.Index;
            var text = root.TryGetProperty("text", out var textEl) ? textEl.GetString()?.Trim() ?? "" : "";
            if (text.Length == 0 || received.TryGetValue(key, out var old) && old.Index == index && old.Text == text) return false;
            if (received.TryGetValue(key, out old) && old.Index != index && segments.TryGetValue(old.Index, out var prior) && prior == old.Text) segments.Remove(old.Index);
            segments[index] = text;
            received[key] = (index, text);
            transcript = Text;
            return true;
        }
        catch (JsonException) { error = "Gnani sent an invalid transcript message."; return false; }
    }
}

// Gnani confirms the selected stream format immediately after the WebSocket
// upgrade. Do not send a queued microphone frame until that contract agrees
// with the PCM framer below.
static class GnaniSttHandshake
{
    public static bool TryAccept(string json, out string error)
    {
        error = "";
        try
        {
            using var doc = JsonDocument.Parse(json); var root = doc.RootElement;
            var type = root.TryGetProperty("type", out var kind) ? kind.GetString() : "";
            if (type == "error") { error = GnaniErrors.SttServer(root.TryGetProperty("message", out var message) ? message.GetString() : null); return false; }
            if (type != "connected") { error = "Gnani cloud speech did not confirm the audio stream."; return false; }
            if (!root.TryGetProperty("config", out var config) || config.ValueKind != JsonValueKind.Object ||
                !config.TryGetProperty("sample_rate", out var rate) || !rate.TryGetInt32(out var sampleRate) || sampleRate != GnaniSttOptions.SampleRate ||
                !config.TryGetProperty("chunk_size", out var chunk) || !chunk.TryGetInt32(out var chunkSize) || chunkSize != GnaniSttOptions.FrameBytes / 2)
            { error = "Gnani cloud speech confirmed an unsupported audio format."; return false; }
            return true;
        }
        catch (JsonException) { error = "Gnani cloud speech sent an invalid connection message."; return false; }
    }
}

// Persistent, real-time Gnani STT WebSocket. Audio is framed and paced here so
// NAudio's callback size cannot cause bursts that confuse the provider's VAD.
sealed class GnaniSttSession : IDisposable
{
    static readonly Uri Endpoint = new("wss://api.vachana.ai/stt/v3/stream");
    readonly GnaniSttOptions options;
    readonly ClientWebSocket socket = new();
    readonly CancellationTokenSource stop = new();
    readonly Channel<byte[]> frames = Channel.CreateBounded<byte[]>(new BoundedChannelOptions(160) { FullMode = BoundedChannelFullMode.DropOldest, SingleReader = true });
    readonly GnaniPcmFramer framer = new();
    readonly GnaniTranscriptAccumulator transcripts = new();
    readonly TaskCompletionSource<bool> handshake = new(TaskCreationOptions.RunContinuationsAsynchronously);
    readonly TaskCompletionSource<bool> senderReady = new(TaskCreationOptions.RunContinuationsAsynchronously);
    readonly object transcriptGate = new();
    TaskCompletionSource<int> nextTranscript = new(TaskCreationOptions.RunContinuationsAsynchronously);
    Task sender, receiver;
    int transcriptCount;
    public event Action<string> Words;
    public event Action<string> Failed;
    public string Error { get; private set; } = "";

    public GnaniSttSession(GnaniSttOptions options) { this.options = options; }

    public async Task StartAsync()
    {
        try
        {
            foreach (var header in options.Headers()) socket.Options.SetRequestHeader(header.Key, header.Value);
            using var connectTimeout = CancellationTokenSource.CreateLinkedTokenSource(stop.Token);
            connectTimeout.CancelAfter(TimeSpan.FromSeconds(8));
            await socket.ConnectAsync(Endpoint, connectTimeout.Token);
            receiver = ReceiveLoop();
            await handshake.Task.WaitAsync(connectTimeout.Token);
            if (Error.Length == 0) { sender = SendLoop(); senderReady.TrySetResult(true); }
        }
        catch (OperationCanceledException) when (stop.IsCancellationRequested) { senderReady.TrySetCanceled(); }
        catch (Exception ex) { Fail(UserError(ex)); }
    }

    public void AddPcm(byte[] pcm)
    {
        if (stop.IsCancellationRequested) return;
        foreach (var frame in framer.Add(pcm)) frames.Writer.TryWrite(frame);
    }

    async Task SendLoop()
    {
        try
        {
            await foreach (var frame in frames.Reader.ReadAllAsync(stop.Token))
            {
                await socket.SendAsync(new ArraySegment<byte>(frame), WebSocketMessageType.Binary, true, stop.Token);
                await Task.Delay(GnaniSttOptions.FrameMilliseconds, stop.Token);
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { Fail(UserError(ex)); }
    }

    async Task ReceiveLoop()
    {
        var bytes = new byte[8192];
        try
        {
            while (!stop.IsCancellationRequested && socket.State == WebSocketState.Open)
            {
                using var text = new MemoryStream(); WebSocketReceiveResult result;
                do { result = await socket.ReceiveAsync(bytes, stop.Token); if (result.MessageType == WebSocketMessageType.Close) return; text.Write(bytes, 0, result.Count); }
                while (!result.EndOfMessage);
                if (result.MessageType != WebSocketMessageType.Text) continue;
                var json = Encoding.UTF8.GetString(text.ToArray());
                if (!handshake.Task.IsCompleted)
                {
                    if (GnaniSttHandshake.TryAccept(json, out var handshakeError)) handshake.TrySetResult(true);
                    else { Fail(handshakeError); return; }
                    continue;
                }
                if (transcripts.AddServerMessage(json, out var words, out var error) && words.Length > 0)
                {
                    SignalTranscript();
                    Words?.Invoke(words);
                }
                else if (error.Length > 0) Fail(error);
            }
        }
        catch (OperationCanceledException) { }
        catch (Exception ex) { Fail(UserError(ex)); }
    }

    public async Task<string> StopAsync()
    {
        Task<int> transcriptAfterStop;
        lock (transcriptGate) transcriptAfterStop = nextTranscript.Task;
        var tail = framer.Flush();
        if (tail.Length > 0) frames.Writer.TryWrite(tail);
        // Gnani closes a VAD segment only after the configured silence. A hotkey
        // release stops the microphone, so explicitly stream PCM silence rather
        // than hoping one padded tail frame is enough to finalize the command.
        var silenceFrames = GnaniSttOptions.SilenceFramesFor(options.MinSilence);
        for (var i = 0; i < silenceFrames; i++) frames.Writer.TryWrite(new byte[GnaniSttOptions.FrameBytes]);
        frames.Writer.TryComplete();
        // A short first utterance can end while the WebSocket is still waiting
        // for its documented connected frame. Give StartAsync a bounded chance
        // to create the sender so already captured PCM is drained in order.
        try { await senderReady.Task.WaitAsync(TimeSpan.FromSeconds(2)); } catch { }
        try { if (sender != null) await sender.WaitAsync(TimeSpan.FromSeconds(4)); } catch { }
        // Wait for a post-release segment, bounded so failed cloud recognition
        // remains an error/fallback rather than an accidental command.
        var finalWait = TimeSpan.FromMilliseconds(Math.Clamp(options.MinSilence + 1500, 1200, 3500));
        try
        {
            await Task.WhenAny(transcriptAfterStop, Task.Delay(finalWait, stop.Token));
        }
        catch (OperationCanceledException) { }
        stop.Cancel();
        try { if (socket.State == WebSocketState.Open) await socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "end of turn", CancellationToken.None); } catch { }
        return Error.Length == 0 ? transcripts.Text : null;
    }

    void Fail(string error)
    {
        if (Error.Length > 0) return;
        Error = error; handshake.TrySetException(new InvalidOperationException(error)); senderReady.TrySetException(new InvalidOperationException(error)); Failed?.Invoke(error); frames.Writer.TryComplete();
    }
    internal static string UserError(Exception ex) => ex switch
    {
        OperationCanceledException => "Gnani cloud speech timed out. Try again or select Local Whisper.",
        WebSocketException socket => GnaniErrors.SttTransport(socket.Message),
        _ => "Gnani cloud speech stopped unexpectedly."
    };
    void SignalTranscript()
    {
        lock (transcriptGate)
        {
            transcriptCount++;
            nextTranscript.TrySetResult(transcriptCount);
            nextTranscript = new(TaskCreationOptions.RunContinuationsAsynchronously);
        }
    }
    public void Dispose() { stop.Cancel(); handshake.TrySetCanceled(); senderReady.TrySetCanceled(); socket.Dispose(); stop.Dispose(); }
}

sealed record GnaniTtsOptions(string ApiKey, string Model, string Voice, string Language, double Speed, int TimeoutSeconds)
{
    public const int SampleRate = 24000;
    public static bool TryCreate(string key, string model, string voice, string language, double speed, int timeoutSeconds, out GnaniTtsOptions options, out string error)
    {
        key = key?.Trim() ?? ""; model = model?.Trim() ?? ""; voice = voice?.Trim() ?? ""; language = language?.Trim() ?? "";
        if (key.Length == 0) { options = null; error = "Gnani speech output needs a saved key."; return false; }
        if (!GnaniVoiceCatalog.IsKnownModel(model) || !GnaniVoiceCatalog.IsKnownLanguage(language) || !GnaniVoiceCatalog.IsVoiceForModel(model, voice) || speed is < .85 or > 1.15 || timeoutSeconds is < 3 or > 60)
        { options = null; error = "Gnani speech output settings are invalid."; return false; }
        options = new(key, model, voice, language, speed, timeoutSeconds); error = ""; return true;
    }
    public static bool TryFromPrefs(out GnaniTtsOptions options, out string error)
    {
        GnaniCredentials.TryGet(out var key, out _);
        return TryCreate(key, Prefs.Str("gnaniTtsModel"), Prefs.Str("gnaniTtsVoice"), Prefs.Str("gnaniTtsLanguage"), Prefs.Num("gnaniTtsSpeed"), (int)Prefs.Num("ttsTimeout"), out options, out error);
    }
}

// A request carries no credential and never retains the spoken text after the
// WebSocket call. Its diagnostic description is deliberately limited to public
// voice settings, so Settings can compare reply routes without leaking a key.
sealed record GnaniTtsRequest(GnaniTtsOptions Options, string Text)
{
    public string Configuration => $"{Options.Model} / {Options.Voice} / {Options.Language} / {Options.Speed:0.00}x";
}

// Pure protocol parser: unit/self-tests feed it mock messages, never a socket.
sealed class GnaniTtsMessageAccumulator
{
    int? lastChunk;
    public bool Complete { get; private set; }
    public bool AddServerMessage(string json, out byte[] audio, out string error)
    {
        audio = Array.Empty<byte>(); error = "";
        try
        {
            using var doc = JsonDocument.Parse(json); var root = doc.RootElement;
            var type = root.TryGetProperty("type", out var t) ? t.GetString() : "";
            if (type == "start") return true;
            if (type == "error") { error = GnaniErrors.TtsServer(root.TryGetProperty("message", out var m) ? m.GetString() : null); return false; }
            if (type is not ("audio" or "complete") || !root.TryGetProperty("data", out var data) || data.ValueKind != JsonValueKind.Object) { error = "Gnani sent an invalid speech response."; return false; }
            var index = data.TryGetProperty("chunk_index", out var i) && i.TryGetInt32(out var n) ? n : -1;
            if (index < 0 || lastChunk is int previous && index <= previous) { error = "Gnani sent audio chunks out of order."; return false; }
            lastChunk = index;
            var final = data.TryGetProperty("is_final", out var f) && f.ValueKind == JsonValueKind.True;
            var base64 = data.TryGetProperty("audio", out var a) ? a.GetString() ?? "" : "";
            if (type == "complete")
            {
                if (!final || base64.Length != 0) { error = "Gnani sent an invalid completion response."; return false; }
                Complete = true; return true;
            }
            if (final || base64.Length == 0) { error = "Gnani sent an invalid audio response."; return false; }
            audio = Convert.FromBase64String(base64);
            if (audio.Length == 0 || audio.Length % 2 != 0) { error = "Gnani sent malformed PCM audio."; return false; }
            return true;
        }
        catch (FormatException) { error = "Gnani sent malformed audio."; return false; }
        catch (JsonException) { error = "Gnani sent an invalid speech response."; return false; }
    }
}

interface ITextToSpeechProvider
{
    string Name { get; }
    Task<SpeechOutputResult> SpeakAsync(string text, CancellationToken cancellationToken, Action<byte[]> onAudio);
}

sealed record SpeechOutputResult(bool Ok, string Provider, string Error = "", bool FirstAudio = false);

sealed class GnaniTtsProvider : ITextToSpeechProvider
{
    static readonly Uri Endpoint = new("wss://api.vachana.ai/api/v1/tts");
    readonly GnaniTtsOptions options;
    public string Name => "Gnani Cloud";
    public GnaniTtsProvider(GnaniTtsOptions options) { this.options = options; }
    internal string RequestJson(string text) => RequestJson(new GnaniTtsRequest(options, text));
    internal string RequestJson(GnaniTtsRequest request) => JsonSerializer.Serialize(new { text = request.Text, voice = request.Options.Voice, model = request.Options.Model, language = request.Options.Language, speed = request.Options.Speed, audio_config = new { sample_rate = GnaniTtsOptions.SampleRate, num_channels = 1, sample_width = 2, encoding = "linear_pcm", container = "raw" } });

    public async Task<SpeechOutputResult> SpeakAsync(string text, CancellationToken cancellationToken, Action<byte[]> onAudio)
    {
        using var socket = new ClientWebSocket();
        try
        {
            socket.Options.SetRequestHeader("X-API-Key-ID", options.ApiKey);
            socket.Options.SetRequestHeader("Content-Type", "application/json");
            using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
            timeout.CancelAfter(TimeSpan.FromSeconds(options.TimeoutSeconds));
            await socket.ConnectAsync(Endpoint, timeout.Token);
            var request = RequestJson(new GnaniTtsRequest(options, text));
            await socket.SendAsync(Encoding.UTF8.GetBytes(request), WebSocketMessageType.Text, true, timeout.Token);
            var parser = new GnaniTtsMessageAccumulator(); var buf = new byte[8192]; var first = false;
            while (!parser.Complete)
            {
                using var message = new MemoryStream(); WebSocketReceiveResult result;
                do { result = await socket.ReceiveAsync(buf, timeout.Token); if (result.MessageType == WebSocketMessageType.Close) return new(false, Name, "Gnani closed speech output before completion."); message.Write(buf, 0, result.Count); } while (!result.EndOfMessage);
                if (result.MessageType != WebSocketMessageType.Text) return new(false, Name, "Gnani sent an unexpected speech response.");
                if (!parser.AddServerMessage(Encoding.UTF8.GetString(message.ToArray()), out var audio, out var error)) return new(false, Name, error);
                if (audio.Length > 0) { onAudio(audio); first = true; }
            }
            try { await socket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "complete", CancellationToken.None); } catch { }
            return new(true, Name, "", first);
        }
        catch (OperationCanceledException) { return new(false, Name, "Gnani speech output timed out or was cancelled."); }
        catch (WebSocketException error) { return new(false, Name, GnaniErrors.TtsTransport(error.Message)); }
        catch { return new(false, Name, "Gnani speech output failed."); }
    }
}
