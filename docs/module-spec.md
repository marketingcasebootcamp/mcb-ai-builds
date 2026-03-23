# Module specification

---

## Universal structure (all types)

```
[module-slug]/
├── README.md
├── metadata.yaml
└── examples/
    ├── input-1.md
    └── output-1.md
```

## README required sections

```markdown
# [Module Name]

> One-sentence summary.

## What it does
## Who it's for
## Inputs
## Outputs
## Setup        ← required if API keys or installation steps are needed
## How to use it
## Example
## Limitations
## Related modules
```

---

## Metadata schema

```yaml
name: Human Readable Module Name
slug: module-slug-in-kebab-case
type: skill | prompt | agent | app | google-script | template
category: case-practice | campaign-ops | analytics | interview-prep | content | reporting | planning
platform: claude | any-llm | streamlit | html | react | nextjs | google-sheets | google-docs | notion
owner: contributor-github-handle
summary: One sentence. Under 120 characters.
audience:
  - aspiring-marketer
inputs:
  - description of input 1
outputs:
  - description of output 1
requires_api: true | false
difficulty: beginner | intermediate | advanced
status: draft | stable | deprecated
license: mit
mcb_featured: false
version: "1.0"
```

---

## Category definitions

| Category | Covers |
|---|---|
| `case-practice` | Practice case generation and evaluation |
| `campaign-ops` | Campaign planning, execution, audit, naming |
| `analytics` | Data interpretation, KPI calculation, metrics |
| `interview-prep` | Mock interview prep, JD analysis |
| `content` | Copy, creative brief, messaging |
| `reporting` | Report structuring, insight writing |
| `planning` | Strategy, channel planning, go-to-market |
