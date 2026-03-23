# API Key Setup

Some apps in this repo require an API key to run.
This guide explains how to set that up safely.

---

## Why we do it this way

API keys are like passwords.
You should never share them publicly or upload them to GitHub.

This setup keeps your key on your own computer only —
it never gets pushed to the repo, even by accident.

---

## How it works

Every app that needs an API key includes two files:

`.env.example` — checked into the repo, safe to share, contains no real keys:
```
ANTHROPIC_API_KEY=your-key-here
```

`.env` — lives only on your computer, contains your real key:
```
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
```

The `.gitignore` file in this repo blocks `.env` from ever being
uploaded to GitHub — even if you forget.

---

## Step-by-step setup

**1. Find the `.env.example` file**

Every app that needs an API key has a `.env.example` file in its folder.

**2. Make a copy and rename it**

In the same folder, create a new file called `.env`
(remove the word "example" from the filename).

On Mac/Linux terminal:
```bash
cp .env.example .env
```

On Windows, just duplicate the file and rename it manually.

**3. Paste your real API key**

Open your `.env` file and replace `your-key-here` with your actual key.

**4. Get an Anthropic API key**

Go to console.anthropic.com
Sign in or create an account
Go to API Keys → Create Key
Copy the key and paste it into your `.env` file

**5. Never share your `.env` file**

Don't send it to anyone. Don't upload it anywhere.
The `.gitignore` already blocks it from GitHub — but good to know why.

---

## Running a Streamlit app

Once your `.env` is set up:

**1. Make sure Python is installed**
Download from python.org if needed. Python 3.9 or higher recommended.

**2. Navigate to the app folder in your terminal**
```bash
cd apps/streamlit/[app-name]
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Run the app**
```bash
streamlit run app.py
```

**5. Your browser opens automatically at http://localhost:8501**

---

## Running a web app

Web apps are simpler — most just open in a browser directly.
Check the app's own README for specific instructions.
Some may require `npm install` if they use Node.js.

---

## Common errors

**"No API key found" error in a Streamlit app**
Your `.env` file is missing or in the wrong folder.
Make sure `.env` is inside the same app folder as `app.py`.

**`streamlit: command not found`**
Run `pip install streamlit` first.

**`ModuleNotFoundError`**
Run `pip install -r requirements.txt` again from the correct folder.
