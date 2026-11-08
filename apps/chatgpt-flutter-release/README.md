# Flutter Release Check for ChatGPT

A remote MCP server that brings the [Flutter Release Kit](../../README.md) rules into ChatGPT. Ask "will Play reject READ_SMS?" or paste a manifest, and ChatGPT answers from these rules instead of from memory.

| Tool | What it does |
|---|---|
| `audit_flutter_permissions` | Audits pasted `AndroidManifest.xml`, `Info.plist` and `pubspec.yaml` |
| `look_up_android_permission` | Risk tier, policy and draft declaration for one permission |
| `check_google_play_listing` | Character limits and flagged wording |
| `check_app_store_listing` | Character limits, keyword formatting and wasted keywords |
| `plan_version_bump` | Next version line and git tag, always raising the build number |

Every tool is read-only and needs no account. The audit and version tools run the same `scripts/` as the Claude Code plugin, so both products stay in step.

## Run locally

From this folder:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/uvicorn server:app --port 8000
```

The endpoint is `http://127.0.0.1:8000/mcp`. To explore it by hand:

```bash
npx @modelcontextprotocol/inspector@latest
```

Choose the Streamable HTTP option and enter that URL.

## Test

```bash
.venv/bin/python -m unittest tests/test_server.py
```

## Deploy

ChatGPT needs a stable public HTTPS URL. Any container host works. Build from the **repository root**:

```bash
docker build -f apps/chatgpt-flutter-release/Dockerfile -t flutter-release-check .
```

Set `OPENAI_APPS_CHALLENGE` to the domain verification token when OpenAI gives you one. The server returns it at `/.well-known/openai-apps-challenge`. `/health` is available for your host's health check.

Keep request logging off wherever you host it. The server does not log file contents, and the Dockerfile disables access logs.

## Connect to ChatGPT

1. Open `chatgpt.com/plugins`.
2. Click the plus button and choose to add a custom MCP server.
3. Enter a name and description, then your public URL ending in `/mcp`.
4. Choose no authentication, review the warning, and confirm.
5. Create it as a plugin and review the discovered tools.

Account and workspace policies decide whether custom servers are available to you.

## Submit to the directory

Check OpenAI's [submission guide](https://developers.openai.com/apps-sdk/deploy/submission) first, as the requirements change. You will need a verified developer identity, the deployed URL with domain verification, a video walkthrough, and these listing details:

- **Display name:** Flutter Release Check
- **Short description:** Catch store rejections early
- **Privacy policy:** a public HTTPS link to [PRIVACY.md](PRIVACY.md)
- **Terms and website:** public HTTPS links, such as the repository's LICENSE and README

### Positive test cases

| Prompt | Expected tool | Expected result |
|---|---|---|
| Will Google Play accept READ_SMS for my OTP screen? | `look_up_android_permission` | Restricted; recommends SMS Retriever |
| Audit this AndroidManifest.xml: *(manifest with READ_SMS)* | `audit_flutter_permissions` | READ_SMS listed as restricted |
| Is this App Store keyword list fine? `budget, budget,money` | `check_app_store_listing` | Reports spaces and the duplicate |
| Does "Ledger - Simple Expense Tracker For Everyone" fit as a Play title? | `check_google_play_listing` | Reports it is over 30 characters |
| My version is 1.4.2+37. What is the next minor release? | `plan_version_bump` | `version: 1.5.0+38`, tag `v1.5.0` |

### Negative test cases

| Prompt | Expected behaviour |
|---|---|
| Write me a Flutter login screen. | No tool is called |
| What is the weather in Hyderabad? | No tool is called |
| Publish my app to Google Play now. | No tool is called; explains it can only check, not publish |
