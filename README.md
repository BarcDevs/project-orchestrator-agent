# HealEase Project Orchestrator Agent

AI-powered task orchestration for HealEase MVP development. Analyzes Notion tasks and generates atomic executable actions via Claude.

## Architecture (WAT Framework)

- **Workflows** (`workflows/`) — SOPs defining what to do
- **Agents** — Claude orchestrating task analysis + execution
- **Tools** (`tools/`) — Python scripts executing deterministic tasks

## How It Works

1. **Daily Sync** — `sync_notion_daily.py` fetches task data from Notion
2. **Task Analysis** — Claude AI analyzes next priority task
3. **Message Generation** — Generates Execution Atomizer format guidance
4. **Discord Notify** — Posts to Discord channel for visibility

## Setup

### Requirements
- Python 3.8+
- API keys (see below)

### Install
```bash
pip install requests python-dotenv anthropic
```

### Environment Variables

Create `.env` file (see `.env.example`):
```
NOTION_API_KEY=your_notion_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
DISCORD_API_KEY=your_discord_bot_token
DISCORD_CHANNEL_ID=your_discord_channel_id
```

### GitHub Secrets Setup

For remote agent execution, add these to repo secrets (`Settings > Secrets and variables > Actions`):
- `NOTION_API_KEY`
- `ANTHROPIC_API_KEY`
- `DISCORD_API_KEY`
- `DISCORD_CHANNEL_ID`

## Usage

### Local Testing
```bash
# Fetch tasks from Notion
python tools/sync_notion_daily.py

# Analyze + post to Discord
python tools/discord_notify.py
```

### Automated Scheduling

Remote agent runs daily at 8pm UTC (11pm Asia/Jerusalem).

View status: https://claude.ai/code/scheduled

## Task Format (Execution Atomizer)

Claude generates atomic actions with this structure:

```
🔧 ATOMIC NEXT ACTION

Task: [single atomic action - one layer only]

Layer: [service | controller | route | UI component | database]

File: [exact file path]

What to do:
- [step 1]
- [step 2]

Done when:
- [measurable result]
- [verifiable condition]

Test:
- [verification method]

Time estimate:
~[minutes] minutes
```

## Cost

- Claude Haiku 4.5: ~$0.005 per task analysis
- Daily run: ~$0.15/month

## Tools

### sync_notion_daily.py
Fetches Notion database (orchestration + timeline), extracts task metadata, saves to `.tmp/notion_sync.json`.

**Input:** Notion API key + database IDs (hardcoded)
**Output:** JSON with tasks sorted by priority/status

### discord_notify.py
Picks next task → calls Claude → generates Atomizer message → posts to Discord.

**Input:** `.tmp/notion_sync.json`
**Output:** Discord message
**Dependencies:** Claude API + Discord bot

## Workflows

See `workflows/` for SOPs (task-specific implementation guides).

## Debugging

Tools output debug logs to stderr:
```bash
python tools/discord_notify.py 2>&1 | grep CLAUDE
```

Look for:
- `[CLAUDE] Task picked: ...` — which task selected
- `[CLAUDE] ✓ Message generated` — API call succeeded
- `[DISCORD] ✓ Message sent` — Discord delivery confirmed
