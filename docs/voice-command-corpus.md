# Voice command corpus

Use this corpus only during a deliberate development smoke test with the chosen
speech provider. It is not an automated desktop test and must not be sent to
Gnani by CI.

For each entry, speak the phrase three times at normal volume, record the final
transcript shown by Silly, and record whether the expected typed route was
selected. Score a run as `correct routes / 30`; keep the unmodified transcripts
only in the local test worksheet, not in Git or diagnostics.

| Phrase | Expected route | Expected query or target |
| --- | --- | --- |
| Open Notepad | application | Notepad |
| Open Chrome | application | Chrome |
| Open YouTube | URL | youtube.com homepage |
| Go to GitHub | URL | github.com |
| Search the web for the latest React tutorial | search | Google, `latest React tutorial` |
| Search YouTube for React tutorials | search | YouTube, `React tutorials` |
| Go to YouTube and search for Raftaar | search | YouTube, `Raftaar` |
| Play Raftaar music on YouTube | search | YouTube, `Raftaar` (results only) |
| YouTube pe Raftaar ke songs chalao | search | YouTube, `Raftaar` (results only) |
| YouTube par React tutorials search karo | search | YouTube, `React tutorials` |
| यूट्यूब पर रफ़्तार के गाने चलाओ | search | YouTube, `रफ़्तार` (results only) |
| यूट्यूब पर रिएक्ट ट्यूटोरियल खोजो | search | YouTube, `रिएक्ट ट्यूटोरियल` |

Measure transcription and routing separately: a transcript can differ in
punctuation or capitalization and still be a correct route, while an unintended
action is always a failure. There is no live-provider score in this repository:
obtaining one consumes the account's Gnani quota and needs an explicit manual
run.
