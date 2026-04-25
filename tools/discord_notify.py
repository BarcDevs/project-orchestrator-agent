#!/usr/bin/env python3
"""
Task orchestration tool for WAT framework.
Picks next task based on priority + status, uses Claude AI to generate
contextual execution guidance, sends to Discord.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

try:
    import requests
    from dotenv import load_dotenv
    from anthropic import Anthropic
except ImportError:
    print("Required packages not installed. Run: pip install requests python-dotenv anthropic", file=sys.stderr)
    sys.exit(1)

project_root = Path(__file__).parent.parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

def send_discord_message(channel_id, content):
    """Send message to Discord channel."""
    try:
        bot_token = os.getenv("DISCORD_API_KEY")
        if not bot_token:
            raise Exception("DISCORD_API_KEY not set")

        headers = {
            "Authorization": f"Bot {bot_token}",
            "Content-Type": "application/json"
        }

        msg_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        print(f"\n[DISCORD] Sending message to channel {channel_id}...", file=sys.stderr)
        msg_response = requests.post(
            msg_url,
            headers=headers,
            json={"content": content}
        )
        msg_response.raise_for_status()
        print(f"[DISCORD] ✓ Message sent successfully", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[DISCORD] ✗ Error sending message: {e}", file=sys.stderr)
        return False

def pick_next_task(tasks):
    """Pick next task: In Progress > Critical Ready > High Ready > Medium Ready."""
    in_progress = [t for t in tasks if t.get("status") == "In Progress"]
    if in_progress:
        return in_progress[0]

    for priority in ["Critical", "High", "Medium", "Low"]:
        ready = [t for t in tasks if t.get("status") == "Ready" and t.get("priority") == priority]
        if ready:
            return ready[0]

    return None

def generate_atomic_message_with_claude(task, structure=None):
    """Use Claude to generate intelligent Execution Atomizer message."""
    try:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise Exception("ANTHROPIC_API_KEY not set in .env")

        print(f"\n[CLAUDE] Task picked: '{task.get('title', 'Unknown')}'", file=sys.stderr)
        print(f"[CLAUDE] Priority: {task.get('priority', 'Medium')} | Status: {task.get('status', 'Ready')}", file=sys.stderr)

        # Build structure reference from Notion data
        structure_ref = ""
        if structure:
            structure_ref = "\n## Project Architecture (from Notion)\n\n"
            by_layer = {}
            for item in structure:
                layer = item.get("Layer", "Unknown")
                if layer not in by_layer:
                    by_layer[layer] = []
                by_layer[layer].append(item)

            for layer, items in by_layer.items():
                structure_ref += f"**{layer}:**\n"
                for item in items:
                    root = item.get("Root Path", "")
                    path = item.get("Path", "")
                    full_path = f"{root}/{path}" if root else path
                    name = item.get("Name", "Unknown")
                    purpose = item.get("Purpose", "")
                    structure_ref += f"- {name} ({full_path}): {purpose}\n"
        else:
            structure_ref = "\n## Project Architecture\n(Structure data not available)\n"

        client = Anthropic()

        prompt = f"""You are an AI agent orchestrating HealEase MVP development. Analyze this task and generate an Execution Atomizer action with VISUAL FLAIR.

{structure_ref}

## Task

📌 Title: {task.get('title', 'Unknown')}
📝 Description: {task.get('notes', '')}
🎯 Priority: {task.get('priority', 'Medium')}
⏳ Status: {task.get('status', 'Ready')}
📅 Due: {task.get('due_date', 'TBD')}

## Generate Execution Atomizer Action

Format:

🔧 ATOMIC NEXT ACTION

Task: [one atomic action - single layer only]

Layer: [ONE ONLY: service | controller | route | UI component | database | middleware]

Location: [Describe location functionally based on structure above. DO NOT guess exact paths. Example: "SERVER: src/services/" or "CLIENT: src/components/check-in/"]

What to do:
🎯 [specific step 1]
🎯 [specific step 2]
🎯 [specific step 3 if needed]

Done when:
🔍 [measurable result 1]
🔍 [verifiable condition 2]

Test:
🧪 [how to verify locally]

Time estimate:
⏱️ ~[realistic minutes] minutes

**RULES:**
- Use STRUCTURE above as source of truth
- Describe location functionally (don't hallucinate exact paths)
- Make it specific to THIS task
- Use relevant emojis (⚙️ backend, 🎨 UI, 🗄️ database)
- Pick ONLY first layer if multiple layers involved (service before controller before route before UI)
"""

        print(f"[CLAUDE] Calling Claude Haiku API...", file=sys.stderr)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        response_text = message.content[0].text
        token_info = f"input={message.usage.input_tokens}, output={message.usage.output_tokens}"
        print(f"[CLAUDE] ✓ Message generated ({token_info})", file=sys.stderr)
        print(f"[CLAUDE] Response preview: {response_text[:80]}...", file=sys.stderr)

        return response_text

    except Exception as e:
        print(f"[CLAUDE] ✗ ERROR: {e}", file=sys.stderr)
        return f"⚠️ Error generating message: {e}"

def format_status(tasks, sync_data):
    """Generate status message via Claude AI."""
    print(f"\n[NOTIFY] Sync status: {sync_data.get('status')}", file=sys.stderr)
    print(f"[NOTIFY] Total tasks: {sync_data.get('task_count', 0)}", file=sys.stderr)

    if sync_data.get("status") != "synced":
        return f"❌ Sync failed: {sync_data.get('error', 'Unknown error')}"

    next_task = pick_next_task(tasks)

    if next_task:
        print(f"[NOTIFY] Generating AI message...", file=sys.stderr)
        structure = sync_data.get("structure", [])
        return generate_atomic_message_with_claude(next_task, structure)

    return "✅ No tasks ready. All caught up!"

def notify():
    """Send task status to Discord."""
    sync_file = project_root / ".tmp" / "notion_sync.json"

    if not sync_file.exists():
        print(f"Sync file not found: {sync_file}", file=sys.stderr)
        return False

    try:
        with open(sync_file) as f:
            sync_data = json.load(f)

        tasks = sync_data.get("tasks", [])
        message = format_status(tasks, sync_data)
        channel_id = os.getenv("DISCORD_CHANNEL_ID")

        if not channel_id:
            raise Exception("DISCORD_CHANNEL_ID not set")

        return send_discord_message(channel_id, message)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = notify()
    sys.exit(0 if success else 1)
