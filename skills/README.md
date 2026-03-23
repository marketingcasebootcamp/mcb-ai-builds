# Skills

Installable Claude Skills for marketing tasks.

Each skill follows the exact Claude SKILL.md specification and can be installed directly in Claude.

---

## What a skill is

A Claude Skill is a reusable, installable capability that runs inside Claude.
Install it once and call it by name mid-conversation.

Skills in this folder are built for real, repeatable marketing tasks —
not generic AI responses, but structured tools with consistent output.

---

## Browse skills

| Slug | Summary | Category |
|---|---|---|
| *(coming soon)* | | |

---

## Install a skill

Each skill folder contains a `SKILL.md` file formatted as a direct prompt with YAML frontmatter.

**Claude Code (slash command):**
```bash
cp skills/<slug>/SKILL.md .claude/commands/<slug>.md
```
Then invoke with `/<slug>` in Claude Code.

**Claude.ai Project:**
Paste the `SKILL.md` contents into your Project's custom instructions.

---

## Want the full experience?

These skills give you core capabilities.
For structured practice with guided feedback, personalized cases, and AI tutoring:

→ **[MCB.AI](https://mcb.ai?utm_source=github&utm_medium=module-readme&utm_campaign=skills-readme)**
