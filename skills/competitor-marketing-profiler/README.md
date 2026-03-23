# Competitor Marketing Profiler

> Head-to-head competitive marketing analysis — positioning, messaging, channels, and opportunities in one structured report.

---

## What it does

You give it two URLs — yours and a competitor's. It researches both brands using web search, reconstructs how each is positioned, maps where they show up across channels, identifies where the competitor is weak, and tells you exactly where your brand has room to move.

The output is reporting-ready. Not a notes dump. A structured analysis you can paste into a doc and walk into a meeting with.

---

## Who it's for

Entry to mid-level marketers who need to understand the competitive landscape but don't have hours to spend opening tabs and writing observations manually. No strategy authority required — this is research and analysis work, not a strategic mandate.

Also useful for:
- Marketing job candidates researching a company before an interview
- Freelancers onboarding a new client and needing to get up to speed fast
- Anyone building a campaign and wanting to know what they're up against

---

## Inputs

| Input | Required? | What to provide |
|---|---|---|
| Your brand name + website URL | ✅ Yes | Your homepage or main product page |
| Competitor name + website URL | ✅ Yes | Their homepage or main product page |
| Your target audience | Recommended | 1–2 sentences — who you're trying to reach |
| Geography / market | Optional | "US only", "Southeast Asia", "global" |
| Specific focus area | Optional | e.g. "Focus especially on their social strategy" |

You don't need to research anything before running this. The skill does the research.

---

## Outputs

A structured 5-section report covering:

1. **Who They Are** — Side-by-side positioning table + comparative narrative
2. **Where They Show Up** — Channel footprint table for both brands with activity signals
3. **How They Think About Their Audience** — Psychographic read, not just demographics
4. **Head-to-Head SWOT** — Relational 2×2 framework: your advantages, their advantages, your opportunities, and watch points where their strength should make you think twice before moving in
5. **Strategic Takeaways** — Three labeled groups: Pursue (open ground you can win), Defend (where to reframe rather than compete head-on), Watch (what to monitor before making a move)

Total length: approximately 1,100–1,200 words. Dense and scannable, not exhaustive.

---

## How to use it

**Requirements:** Web search must be enabled in Claude settings. This skill uses web search actively throughout the process.

1. Install this skill in Claude (paste the SKILL.md content into a Claude Project instruction or custom system prompt)
2. Start a new conversation
3. Provide your brand URL and competitor URL, plus any optional context
4. The skill researches both brands and delivers the full report

**Example prompt:**
```
My brand: Notion — https://notion.so
We're focused on small teams and freelancers who want an all-in-one workspace.

Competitor: Coda — https://coda.io
```

That's it. The skill takes it from there.

---

## Example

See the `examples/` folder for two complete input/output pairs:

- **Example 1** — DTC skincare brand vs competitor, full brand context provided
- **Example 2** — B2B SaaS tool vs competitor, URL only (shows how the skill handles thin inputs and flags gaps)

---

## Limitations

- Requires web search to be enabled — will not work without it
- Cannot access gated content, private ad accounts, or internal analytics
- Social media frequency estimates are approximate — based on visible posts at time of research
- Smaller or newer brands may have limited public footprint; the skill flags this rather than guessing
- Does not analyze pricing, product features, or company financials
- Run one competitor at a time for best depth — this is a focused matchup tool, not a landscape overview

---

## Related modules

- `metrics-to-insight-summary` — turn campaign data into a structured insight narrative
- `brief-to-channel-checklist` — turn a campaign brief into a per-channel execution checklist
- `campaign-debrief-to-lessons` — structure post-campaign learnings

---

## Want the full experience?

This skill gives you the research and analysis layer.

For structured practice with guided feedback, personalized cases, AI tutoring, and progress tracking → [MCB.AI](https://mcb.ai?utm_source=github&utm_medium=module-readme&utm_campaign=competitor-marketing-profiler)
