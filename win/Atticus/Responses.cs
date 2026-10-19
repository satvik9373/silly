namespace Atticus;

// Presentation-only contract shared by deterministic actions and AI workers.
// It carries a confirmed outcome, not a tool command, so speech can never
// cause an action to be replayed.
enum ResponseStatus { Success, Failure, Confirmation, Information }

sealed record AssistantResponse(string DisplayText, string SpokenText, ResponseStatus Status, bool RequiresConfirmation, bool ShouldSpeak)
{
    public static AssistantResponse Success(string text) => new(text, text, ResponseStatus.Success, false, true);
    public static AssistantResponse Failure(string text) => new(text, text, ResponseStatus.Failure, false, true);
    public static AssistantResponse Confirmation(string text) => new(text, text, ResponseStatus.Confirmation, true, true);
    public AssistantResponse ForPreferences()
    {
        if (!ShouldSpeak || Prefs.Str("speechReplyMode") != "brief") return this;
        var stop = SpokenText.IndexOfAny(new[] { '.', '!', '?', '\n' });
        var shortText = (stop > 0 ? SpokenText[..(stop + 1)] : SpokenText).Trim();
        if (shortText.Length > 220) shortText = shortText[..220].TrimEnd() + "…";
        return this with { SpokenText = shortText };
    }
}

sealed class ResponseDeduplicator
{
    readonly HashSet<string> sent = new(StringComparer.Ordinal);
    public bool TryAccept(AssistantResponse response) => sent.Add(response.Status + "\t" + Overlay.TranscriptKey(response.DisplayText));
    public void Reset() => sent.Clear();
}

// The production completion boundary. Keeping this adapter small makes the
// exact same path testable with a fake speaker without replaying an action.
interface IResponseSpeaker
{
    void Say(AssistantResponse response, Action<SpeechOutputResult> done, Action<string> firstAudio);
}

sealed class VoiceResponseSpeaker : IResponseSpeaker
{
    public void Say(AssistantResponse response, Action<SpeechOutputResult> done, Action<string> firstAudio) => Voice.Say(response, done, firstAudio);
}

sealed class ResponseDelivery
{
    readonly IResponseSpeaker speaker;
    readonly ResponseDeduplicator deduplicator = new();
    public ResponseDelivery(IResponseSpeaker speaker) { this.speaker = speaker; }
    public bool Deliver(AssistantResponse response, Action<SpeechOutputResult> done, Action<string> firstAudio)
    {
        if (!deduplicator.TryAccept(response)) return false;
        speaker.Say(response, done, firstAudio);
        return true;
    }
    public void Reset() => deduplicator.Reset();
}

static class SpeechOutputPlan
{
    // A deterministic, testable selection rule; network failure never changes
    // the action result and local output is labelled as local by the caller.
    public static string Select(bool wantsGnani, bool gnaniAvailable, bool localFallback) =>
        wantsGnani && gnaniAvailable ? "Gnani Cloud" : wantsGnani && localFallback ? "Windows local" : wantsGnani ? "Unavailable" : "Windows local";
}
