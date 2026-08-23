# Demo Video Script (aim for 3–4 minutes)

Record your screen (OBS Studio / Loom / QuickTime) at 1080p. Suggested beats:

1. **Hook (10s)** — "Most meeting summarizers just dump a transcript and a
   paragraph. This one turns a meeting into decisions, owned tasks,
   calendar reminders, and a searchable memory."

2. **Upload (20s)** — Show the sidebar upload form. Drop in a short sample
   recording (record a 2–3 min fake "standup" with a friend, or use a
   public sample meeting clip). Point out the status badge moving
   `uploaded → transcribing → summarizing → done`.

3. **The readout (60s)** — Once processing finishes:
   - Point at the **Meeting Health Score** VU meter and its three
     sub-scores (decisiveness / actionability / clarity) — explain this
     is derived from the transcript, not just a word count.
   - Read one **key decision** and one **action item** row, noting the
     owner/deadline/priority were extracted automatically, not typed by
     you.
   - Show the **sentiment pill**.

4. **The "so what" features (60–90s)** — this is what makes it stand out:
   - Click **Download Calendar (.ics)** and actually open it — show the
     reminder land on a real calendar with the owner's name in the title.
   - Click **Download Minutes (.docx)** and open the generated Word doc.
   - Toggle an action item to **done** and show the **Open Tasks** tab
     updating live — "this is every task I owe across every meeting I've
     recorded, in one place."
   - Use the **Ask** box: ask a question about the meeting, then toggle
     "search all meetings" and ask a question that spans two different
     uploaded meetings, showing the semantic search pulling from both.

5. **Under the hood (30s)** — briefly show `llm_service.py`'s structured
   JSON schema and mention it's a *single* forced-JSON call (not five
   chained prompts), and that ASR/LLM providers are swappable via `.env`.

6. **Close (10s)** — repo link, "README has full setup instructions."

## Recording tips
- Prepare 1–2 short sample audio clips in advance (record yourself
  reading a fake meeting with a decision + 2 action items with names
  and dates said out loud — this is what makes extraction look good).
- Do a dry run once before recording so you know how long processing
  takes with your chosen ASR/LLM provider.
- Keep terminal output out of frame unless you're showing the "under the
  hood" beat.
