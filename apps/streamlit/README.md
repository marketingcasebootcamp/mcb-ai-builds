# Apps — Streamlit

Python Streamlit apps for marketing tasks.

---

## Running a Streamlit app

See the [API Key Setup Guide →](../../docs/api-setup.md) for full instructions.

Quick version:
```bash
cd apps/streamlit/[app-name]
cp .env.example .env        # then add your real API key to .env
pip install -r requirements.txt
streamlit run app.py
```

---

## Browse apps

| Slug | Summary | Requires API |
|---|---|---|
| *(coming soon)* | | |

---

## Structure of each app

```
[app-slug]/
├── app.py
├── requirements.txt
├── .env.example     ← committed, shows required keys (no real values)
├── metadata.yaml
├── README.md
└── assets/
```
