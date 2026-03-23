# Contributing to mcb-ai-builds

This guide explains how to submit a module that fits the ecosystem and is likely to be accepted.

---

## Module types we accept

| Type | Currently accepting? | Technical bar |
|---|---|---|
| prompts | Yes | Very low |
| templates | Yes | Very low |
| skills | Yes | Low — follows Claude SKILL.md spec |
| apps/streamlit | Yes | Medium — Python required |
| apps/web | Yes | Medium — HTML/JS/React |
| google-scripts | Yes | Low–medium — Apps Script |
| agents | Not yet | High — MCP protocol |

Start with prompts and templates if you're new to contributing.

---

## Before you submit

1. Does this solve a real, repeatable marketing work task?
2. Does it have a clear input and a useful output?
3. Is it distinct from what already exists in the repo?
4. Would a practicing marketer actually use this?

---

## API key rules

**Never put a real API key in any file you commit.**

- Include a `.env.example` with placeholder values only
- Add a Setup section pointing to `docs/api-setup.md`
- For Streamlit apps: include the standard API key check block at top of `app.py`

PRs containing real API keys will be rejected immediately.

---

## Contribution flow

1. Open a module proposal using the issue template
2. Wait for a green label — idea is approved to build
3. Fork the repo and create a branch: `add/[module-slug]`
4. Build the module following the module spec
5. Open a pull request using the PR template
6. Address review feedback

---

## What gets rejected

- Generic marketing theory summaries
- Modules without real tested examples
- Duplicate modules without meaningful improvement
- Incomplete metadata
- Any file containing a real API key
