#!/usr/bin/env python3
"""
Daily Notion sync tool for HealEase orchestration.
Fetches task data from Notion, extracts structured data, saves to JSON.
WAT framework: Tool layer (deterministic execution). Agent reads output for decisions.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Required packages not installed. Run: pip install requests python-dotenv", file=sys.stderr)
    sys.exit(1)

# Load .env file from project root (if exists - allows local testing)
project_root = Path(__file__).parent.parent
dotenv_path = project_root / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

def fetch_notion_database(db_id):
    """Fetch Notion database pages via Notion API."""
    try:
        api_key = os.getenv("NOTION_API_KEY")
        print(f"[DEBUG] NOTION_API_KEY set: {bool(api_key)}", file=sys.stderr)
        print(f"[DEBUG] NOTION_API_KEY value starts with: {api_key[:10] if api_key else 'NONE'}", file=sys.stderr)
        if not api_key:
            raise Exception("NOTION_API_KEY environment variable not set")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

        # Query the database
        url = f"https://api.notion.com/v1/databases/{db_id}/query"
        response = requests.post(url, headers=headers, json={})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching Notion database: {e}", file=sys.stderr)
        return None

def extract_tasks_from_db(db_response):
    """Parse Notion database query response, extract task metadata."""
    tasks = []

    try:
        if isinstance(db_response, dict) and "results" in db_response:
            for page in db_response["results"]:
                props = page.get("properties", {})

                # Extract property values based on Notion schema
                task = {
                    "title": extract_text(props.get("Task")),
                    "status": extract_select(props.get("Status")),
                    "phase": extract_select(props.get("Phase")),
                    "priority": extract_select(props.get("Priority")),
                    "owner": extract_text(props.get("Owner")),
                    "due_date": extract_date(props.get("Due Date")),
                    "notes": extract_text(props.get("Notes"))
                }

                if task["title"] and task["status"]:
                    tasks.append(task)
    except Exception as e:
        print(f"Error parsing tasks: {e}", file=sys.stderr)

    return tasks

def extract_text(prop):
    """Extract plain text from Notion text property."""
    if not prop or prop.get("type") != "title":
        if prop and prop.get("type") == "rich_text":
            texts = [t.get("plain_text", "") for t in prop.get("rich_text", [])]
            return "".join(texts)
        return ""
    texts = [t.get("plain_text", "") for t in prop.get("title", [])]
    return "".join(texts)

def extract_select(prop):
    """Extract value from Notion select property."""
    if not prop or prop.get("type") != "select":
        return ""
    select = prop.get("select", {})
    return select.get("name", "") if select else ""

def extract_date(prop):
    """Extract date from Notion date property."""
    if not prop or prop.get("type") != "date":
        return ""
    date_obj = prop.get("date", {})
    return date_obj.get("start", "") if date_obj else ""

def sync_notion():
    """
    Sync HealEase Notion: orchestration + structure.
    Extract task data + architecture structure.
    Save to .tmp/notion_sync.json for agent consumption.
    """

    ORCHESTRATION_ID = "896b0f0ff56246d589265d6091c79fa8"
    STRUCTURE_CLIENT_ID = "569c1733e17f4379939daa1242d85664"
    STRUCTURE_SERVER_ID = "cf5967d829b84c6b9226a9d81c2f3010"
    TIMELINE_ID = "3129e15469d28100be18df6e1ce0a984"

    output_dir = Path(".tmp")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "notion_sync.json"

    sync_data = {
        "synced_at": datetime.now().isoformat(),
        "tasks": [],
        "structure": [],
        "timeline": [],
        "task_count": 0,
        "status": "pending",
        "error": None
    }

    try:
        print(f"[{datetime.now().isoformat()}] Syncing HealEase Notion...", file=sys.stderr)

        # Fetch orchestration database
        print(f"Fetching tasks ({ORCHESTRATION_ID})...", file=sys.stderr)
        orch_data = fetch_notion_database(ORCHESTRATION_ID)

        if not orch_data:
            raise Exception("Failed to fetch orchestration database")

        # Extract tasks
        tasks = extract_tasks_from_db(orch_data)
        print(f"Extracted {len(tasks)} tasks", file=sys.stderr)

        # Fetch structure databases (client + server)
        print(f"Fetching client structure ({STRUCTURE_CLIENT_ID})...", file=sys.stderr)
        client_struct_data = fetch_notion_database(STRUCTURE_CLIENT_ID)
        client_structure = extract_tasks_from_db(client_struct_data) if client_struct_data else []
        print(f"Extracted {len(client_structure)} client structure entries", file=sys.stderr)

        print(f"Fetching server structure ({STRUCTURE_SERVER_ID})...", file=sys.stderr)
        server_struct_data = fetch_notion_database(STRUCTURE_SERVER_ID)
        server_structure = extract_tasks_from_db(server_struct_data) if server_struct_data else []
        print(f"Extracted {len(server_structure)} server structure entries", file=sys.stderr)

        structure = client_structure + server_structure

        # Fetch timeline database
        print(f"Fetching timeline ({TIMELINE_ID})...", file=sys.stderr)
        timeline_data = fetch_notion_database(TIMELINE_ID)
        timeline = extract_tasks_from_db(timeline_data) if timeline_data else []
        print(f"Extracted {len(timeline)} timeline entries", file=sys.stderr)

        # Populate sync data
        sync_data["tasks"] = tasks
        sync_data["structure"] = structure
        sync_data["timeline"] = timeline
        sync_data["task_count"] = len(tasks)
        sync_data["status"] = "synced"

        # Summary for agent
        by_priority = {}
        by_status = {}
        for task in tasks:
            by_priority[task.get("priority", "Unknown")] = by_priority.get(task.get("priority", "Unknown"), 0) + 1
            by_status[task.get("status", "Unknown")] = by_status.get(task.get("status", "Unknown"), 0) + 1

        sync_data["summary"] = {
            "by_priority": by_priority,
            "by_status": by_status
        }

    except Exception as e:
        sync_data["status"] = "error"
        sync_data["error"] = str(e)
        print(f"Sync failed: {e}", file=sys.stderr)
        return False

    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(sync_data, f, indent=2)

    print(f"✓ Saved {sync_data['task_count']} tasks to {output_file}", file=sys.stderr)
    print(json.dumps(sync_data, indent=2))
    return True

if __name__ == "__main__":
    success = sync_notion()
    sys.exit(0 if success else 1)
