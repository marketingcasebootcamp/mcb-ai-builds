# mcb-ai-builds

> A collection of open marketing tools, skills, prompts, and templates — built with AI.

Part of the [marketingcasebootcamp](https://github.com/marketingcasebootcamp) open ecosystem.

---

## What this is

Real marketing work involves a lot of repeatable, structured tasks:
turning raw metrics into insights, auditing campaign structure,
generating practice cases, writing test hypotheses.

This repo contains modular, reusable tools for these tasks.
Each module is self-contained with clear inputs, outputs, and usage instructions.

---

## How to use this repo

**Not a developer? Start here.**
You don't need to write code or set anything up to use most of this repo.

- **Prompts** — copy the prompt, paste it into ChatGPT, Claude, or any AI tool, and run it. That's it.
- **Templates** — open in Google Sheets, Notion, or your browser. Ready to use.
- **Web apps** — open the link in your browser. No install.
- **Skills** — paste the `SKILL.md` contents into a Claude Project's custom instructions. One-time setup, then call the skill by name in any conversation.

**Developer or technically comfortable? You can go further.**
- **Skills** — copy `SKILL.md` into `.claude/commands/` to use as a Claude Code slash command
- **Google Scripts** — paste into Google Apps Script and run from your Sheet
- **Streamlit apps** — run locally with `streamlit run app.py` or deploy to Streamlit Cloud
- **Agents** — MCP servers and autonomous agents; see individual READMEs for setup requirements

If a module needs an API key, the README will say so and link to the [API Key Setup Guide →](./docs/api-setup.md).

---

## Module types

| Type | What it is | Technical bar to use |
|---|---|---|
| **skills** | Installable Claude Skills (exact SKILL.md spec) | Low — install in Claude |
| **prompts** | Structured prompts for any LLM | Very low — copy and paste |
| **agents** | MCP servers and autonomous agents (coming soon) | Medium–high |
| **apps/streamlit** | Python Streamlit apps | Low — run locally or deploy |
| **apps/web** | Browser-based tools (React, Next.js, HTML) | Very low — open in browser |
| **google-scripts** | Google Apps Script for Sheets and Google products | Low — paste into Apps Script |
| **templates** | Frameworks, doc structures, Sheet starters | Very low — open and use |

---

## Browse modules

- [Skills →](./skills/)
- [Prompts →](./prompts/)
- [Agents →](./agents/)
- [Apps →](./apps/)
- [Google Scripts →](./google-scripts/)
- [Templates →](./templates/)

---

## Running apps that use AI

Some apps require an API key to run.
**Never put your API key directly in any code file.**
Read the [API Key Setup Guide →](./docs/api-setup.md) before running any app.

---

## Contribute

Want to add a module? Read the [Contribution Guide →](./docs/contribution-guide.md)

---

## The full experience

These modules are open and free to use.
For structured, guided, personalized practice — AI tutoring, custom case generation,
mock interviews, and integrated workflows:

→ **[MCB.AI](https://marketingcasebootcamp.ai)** — AI-powered marketing practice platform

---

## License

MIT — free to use, modify, and build on.
