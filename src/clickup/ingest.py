from src.clickup.client import ClickUpClient
from src.rag.pipeline import store_documents
from datetime import datetime

def format_timestamp(ts):
    """Converts timestamp in ms to ISO8601."""
    try:
        return datetime.fromtimestamp(int(ts) / 1000).isoformat()
    except Exception:
        return None

def build_task_doc(task, list_id, folder_id, space_id, comments=None, activity=None):
    comments = comments or []
    activity = activity or []

    content_parts = [
        f"Task: {task.get('name', '')}",
        task.get("description", "")
    ]

    # 🗨️ Add comments section with timestamps
    if isinstance(comments, list):
        comment_texts = "\n".join([
            f"{format_timestamp(c.get('comment', {}).get('date'))} — {c.get('comment', {}).get('text_content', '')}"
            for c in comments
            if isinstance(c, dict) and isinstance(c.get("comment", {}), dict)
        ])
        if comment_texts.strip():
            content_parts.append(f"\nComments:\n{comment_texts}")

    # 📋 Add activity section with timestamps
    if isinstance(activity, list):
        activity_texts = "\n".join([
            f"{format_timestamp(a.get('date'))} — {a.get('type', '')}: {a.get('text_content', '')}"
            for a in activity if isinstance(a, dict)
        ])
        if activity_texts.strip():
            content_parts.append(f"\nActivity:\n{activity_texts}")

    content = "\n".join(content_parts)

    # 🧑 Assignees
    assignees = task.get("assignees", [])
    assignee_names = ", ".join([
        a.get("username", "Unknown") for a in assignees if isinstance(a, dict)
    ]) if assignees else "Unassigned"

    # 🕒 Created/updated
    created = format_timestamp(task.get("date_created"))
    updated = format_timestamp(task.get("date_updated"))

    # 🏷️ Full metadata
    metadata = {
        "task_id": task.get("id"),
        "status": task.get("status", {}).get("status") if isinstance(task.get("status"), dict) else None,
        "priority": task.get("priority"),
        "assignee": assignee_names,
        "due_date": task.get("due_date"),
        "created_at": created,
        "updated_at": updated,
        "space_id": space_id,
        "list_id": list_id,
        "folder_id": folder_id or "None",
    }

    # 🧹 Remove None values
    metadata = {k: v for k, v in metadata.items() if v is not None}
    return {
        "comments": content,
        "metadata": metadata
    }


def ingest_clickup_tasks(team_id, space_id, namespace="default"):
    client = ClickUpClient()
    all_docs = []

    # 🔍 FOLDERS
    folders = client.get_folders(space_id).get("folders", [])
    print(f"📁 Found {len(folders)} folders in space {space_id}")

    if not folders:
        print(f"⚠️ No folders found in space {space_id} — checking for folderless lists...")

    for folder in folders:
        folder_id = folder["id"]
        lists = client.get_lists(folder_id).get("lists", [])
        print(f"📂 Folder: {folder['name']} ({folder_id}) — {len(lists)} lists")

        for lst in lists:
            tasks = client.get_tasks(lst["id"]).get("tasks", [])
            print(f"📋 List: {lst['name']} ({lst['id']}) — {len(tasks)} tasks")

            for task in tasks:
                try:
                    comments = client.get_task_comments(task["id"]).get("comments", [])
                    activity = client.get_task_activity(task["id"]).get("activities", [])
                    doc = build_task_doc(task, lst["id"], folder_id, space_id, comments, activity)
                    all_docs.append(doc)
                except Exception as e:
                    print(f"❌ Error processing task {task.get('id')}: {str(e)}")

    # 🔍 FOLDERLESS LISTS
    folderless_lists = client.get_folderless_lists(space_id).get("lists", [])
    print(f"📂 Folderless Lists Found: {len(folderless_lists)}")

    for lst in folderless_lists:
        tasks = client.get_tasks(lst["id"]).get("tasks", [])
        print(f"📋 List (No Folder): {lst['name']} ({lst['id']}) — Found {len(tasks)} tasks")

        for task in tasks:
            try:
                comments = client.get_task_comments(task["id"]).get("comments", [])
                activity = client.get_task_activity(task["id"]).get("activities", [])
                doc = build_task_doc(task, lst["id"], folder_id=None, space_id=space_id, comments=comments, activity=activity)
                all_docs.append(doc)
            except Exception as e:
                print(f"❌ Error processing task {task.get('id')}: {str(e)}")


    print(f"\n📦 Prepared {len(all_docs)} documents to store in namespace: {namespace}")
    if all_docs:
        store_documents(all_docs, namespace=namespace)
    else:
        print("❌ No documents to store.")
