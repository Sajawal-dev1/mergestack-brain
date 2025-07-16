from src.clickup.client import ClickUpClient
from src.rag.pipeline import store_documents
from datetime import datetime
import tenacity
# import spacy  # Optional: for keyword extraction
# nlp = spacy.load("en_core_web_sm")  # Load small English model

def format_timestamp(ts):
    """Format timestamp from milliseconds to ISO string and return numeric value."""
    try:
        ts = int(ts) / 1000
        if ts <= 0:
            return None, None
        dt = datetime.fromtimestamp(ts)
        return dt.isoformat(), int(ts * 1000)  # ISO string and milliseconds
    except (TypeError, ValueError, OverflowError):
        return None, None

def extract_keywords(text):
    """Extract keywords using spaCy (optional)."""
    # doc = nlp(text.lower())
    # return [token.text for token in doc if token.is_alpha and not token.is_stop and len(token.text) > 3]
    return []  # Placeholder if spaCy is not used

def build_clickup_docs(task, list_id, folder_id, space_id, comments=None, activity=None, list_name=None, folder_name=None, team_id=None):
    """Build documents for a task, its comments, replies, and activity with enriched content and metadata."""
    comments = comments or []
    activity = activity or []

    task_id = task.get("id", "unknown")
    task_name = task.get("name", "Unnamed Task")
    task_description = task.get("description", "") or "No description provided"
    created, created_ms = format_timestamp(task.get("date_created"))
    updated, updated_ms = format_timestamp(task.get("date_updated"))
    due_date, due_date_ms = format_timestamp(task.get("due_date",'none'))
    assignees = task.get("assignees", [])
    assignee_names = [a.get("username", "Unknown") for a in assignees if isinstance(a, dict)]
    assignee_ids = [a.get("id", "Unknown") for a in assignees if isinstance(a, dict)]
    tags = [t.get("name", "") for t in task.get("tags", []) if isinstance(t, dict)]
    status = task.get("status", {}).get("status", "Unknown") if isinstance(task.get("status"), dict) else "Unknown"
    priority = task.get("priority", "None")
    custom_fields = {cf.get("name", "Unknown"): cf.get("value") for cf in task.get("custom_fields", []) if isinstance(cf, dict)}

    # Generate keywords for hybrid search
    keywords = [task_name.lower()] + [t.lower() for t in tags] + ([status.lower()] if status else [])
    keywords.extend(extract_keywords(task_description))
    if "stripe" in task_name.lower() or any("stripe" in t.lower() for t in tags) or "stripe" in task_description.lower():
        keywords.append("stripe")
    if "integration" in task_name.lower() or any("integration" in t.lower() for t in tags) or "integration" in task_description.lower():
        keywords.append("integration")
    keywords = list(set(keywords))  # Remove duplicates

    base_metadata = {
        "task_id": task_id,
        "space_id": space_id,
        "list_id": list_id,
        "folder_id": folder_id or "None",
        "folder_name": folder_name or "None",
        "list_name": list_name or "None",
        "team_id": team_id or "None",
        "task_name": task_name,
        "created_at": created,
        "created_at_ms": created_ms,
        "updated_at": updated,
        "updated_at_ms": updated_ms,
        "due_date": due_date or "None",
        "due_date_ms": due_date_ms or "None",
        "assignees": assignee_names,
        "assignee_ids": assignee_ids,
        "status": status,
        "priority": priority or "None",
        "tags": tags,
        "custom_fields": custom_fields,
        "comment_count": len(comments),
        "keywords": keywords,
        "source": "clickup"
    }

    docs = []
    discussion_text = []

    # 1. Task Document
    task_content = (
        f"Task: {task_name}\n"
        f"Description: {task_description}\n"
        f"Status: {status}\n"
        f"Priority: {priority}\n"
        f"Due Date: {due_date or 'None'}\n"
        f"Created: {created or 'Unknown'}\n"
        f"Updated: {updated or 'Unknown'}\n"
        f"Assignees: {', '.join(assignee_names) or 'None'}\n"
        f"Tags: {', '.join(tags) or 'None'}\n"
        f"Custom Fields: {', '.join([f'{k}: {v}' for k, v in custom_fields.items()]) or 'None'}"
    )
    if task_name or task_description:
        docs.append({
            "content": task_content.strip(),
            "metadata": {
                **base_metadata,
                "type": "task",
                "date": created[:10] if created else None,
                "full_timestamp": created,
                "timestamp_ms": created_ms
            }
        })

    # 2. Comments + Replies
    for c in comments:
        comment_text = c.get("comment_text", "").strip()
        if not comment_text:
            continue

        comment_ts, comment_ts_ms = format_timestamp(c.get("date"))
        comment_user = c.get("user", {}).get("username", "Unknown")
        comment_user_id = c.get("user", {}).get("id", "Unknown")
        comment_content = (
            f"Task: {task_name}\n"
            f"Comment by {comment_user} on {comment_ts[:10] if comment_ts else 'Unknown'}:\n"
            f"{comment_text}"
        )
        discussion_text.append(comment_content)

        docs.append({
            "content": comment_content.strip(),
            "metadata": {
                **base_metadata,
                "type": "comment",
                "user": comment_user,
                "user_id": comment_user_id,
                "timestamp": comment_ts,
                "timestamp_ms": comment_ts_ms,
                "date": comment_ts[:10] if comment_ts else None,
                "full_timestamp": comment_ts,
                "comment_id": c.get("id")
            }
        })

        for reply in c.get("replies", []):
            reply_text = reply.get("text", "").strip()
            if not reply_text:
                continue

            reply_ts, reply_ts_ms = format_timestamp(reply.get("date"))
            reply_user = reply.get("user", {}).get("username", "Unknown")
            reply_user_id = reply.get("user", {}).get("id", "Unknown")
            reply_content = (
                f"Task: {task_name}\n"
                f"Reply to comment by {comment_user} by {reply_user} on {reply_ts[:10] if reply_ts else 'Unknown'}:\n"
                f"{reply_text}"
            )
            discussion_text.append(reply_content)

            docs.append({
                "content": reply_content.strip(),
                "metadata": {
                    **base_metadata,
                    "type": "reply",
 "user": reply_user,
                    "user_id": reply_user_id,
                    "timestamp": reply_ts,
                    "timestamp_ms": reply_ts_ms,
                    "date": reply_ts[:10] if reply_ts else None,
                    "full_timestamp": reply_ts,
                    "parent_comment_id": c.get("id")
                }
            })

    # 3. Activity Items
    for a in activity:
        act_ts, act_ts_ms = format_timestamp(a.get("date"))
        act_text = a.get("text_content", "").strip()
        act_type = a.get("type", "Unknown")
        act_user = a.get("username", "Unknown")
        act_user_id = a.get("user_id", "Unknown")
        if not act_text:
            continue

        act_content = (
            f"Task: {task_name}\n"
            f"Activity by {act_user} on {act_ts[:10] if act_ts else 'Unknown'} ({act_type}):\n"
            f"{act_text}"
        )

        docs.append({
            "content": act_content.strip(),
            "metadata": {
                **base_metadata,
                "type": "activity",
                "user": act_user,
                "user_id": act_user_id,
                "timestamp": act_ts,
                "timestamp_ms": act_ts_ms,
                "date": act_ts[:10] if act_ts else None,
                "full_timestamp": act_ts,
                "activity_type": act_type
            }
        })

    # 4. Aggregated Discussion Document
    if discussion_text:
        docs.append({
            "content": "\n\n".join(discussion_text).strip(),
            "metadata": {
                **base_metadata,
                "type": "discussion",
                "date": created[:10] if created else None,
                "full_timestamp": created,
                "timestamp_ms": created_ms
            }
        })

    return docs

def ingest_clickup_tasks(team_id, space_id, namespace="default"):
    """Ingest ClickUp tasks, comments, and activity into Pinecone."""
    client = ClickUpClient()
    all_docs = []

    # Retry decorator for API calls
    @tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_fixed(2))
    def get_replies(comment_id):
        return client.get_comment_thread(comment_id)

    def fetch_replies_for_comments(raw_comments):
        """Fetch replies for each comment with retry logic."""
        for c in raw_comments:
            comment_id = c.get("id")
            if comment_id:
                try:
                    replies = get_replies(comment_id)
                    c["replies"] = [
                        {
                            "text": r.get("comment_text", ""),
                            "date": r.get("date"),
                            "user": r.get("user", {})
                        }
                        for r in replies if isinstance(r, dict) and r.get("comment_text", "").strip()
                    ]
                except Exception as reply_err:
                    print(f"⚠️ Failed to fetch replies for comment {comment_id}: {str(reply_err)}")
                    c["replies"] = []
        return raw_comments

    # Fetch folders
    try:
        folders = client.get_folders(space_id).get("folders", [])
        print(f"📁 Found {len(folders)} folders in space {space_id}")
    except Exception as e:
        print(f"❌ Error fetching folders for space {space_id}: {str(e)}")
        folders = []

    if not folders:
        print(f"⚠️ No folders found in space {space_id} — checking for folderless lists...")

    # Process folders
    for folder in folders:
        folder_id = folder.get("id")
        folder_name = folder.get("name", "Unnamed Folder")
        try:
            lists = client.get_lists(folder_id).get("lists", [])
            print(f"📂 Folder: {folder_name} ({folder_id}) — {len(lists)} lists")
        except Exception as e:
            print(f"❌ Error fetching lists for folder {folder_id}: {str(e)}")
            lists = []

        for lst in lists:
            list_id = lst.get("id")
            list_name = lst.get("name", "Unnamed List")
            try:
                tasks = client.get_tasks(list_id).get("tasks", [])
                print(f"📋 List: {list_name} ({list_id}) — {len(tasks)} tasks")
            except Exception as e:
                print(f"❌ Error fetching tasks for list {list_id}: {str(e)}")
                tasks = []

            for task in tasks:
                try:
                    raw_comments = client.get_task_comments(task.get("id")).get("comments", [])
                    raw_comments = fetch_replies_for_comments(raw_comments)
                    activity = client.get_task_activity(task.get("id")).get("activities", [])
                    docs = build_clickup_docs(
                        task=task,
                        list_id=list_id,
                        folder_id=folder_id,
                        space_id=space_id,
                        comments=raw_comments,
                        activity=activity,
                        list_name=list_name,
                        folder_name=folder_name,
                        team_id=team_id
                    )
                    all_docs.extend(docs)
                except Exception as e:
                    print(f"❌ Error processing task {task.get('id', 'unknown')}: {str(e)}")

    # Process folderless lists
    try:
        folderless_lists = client.get_folderless_lists(space_id).get("lists", [])
        print(f"📂 Folderless Lists Found: {len(folderless_lists)}")
    except Exception as e:
        print(f"❌ Error fetching folderless lists for space {space_id}: {str(e)}")
        folderless_lists = []

    for lst in folderless_lists:
        list_id = lst.get("id")
        list_name = lst.get("name", "Unnamed List")
        try:
            tasks = client.get_tasks(list_id).get("tasks", [])
            print(f"📋 List (No Folder): {list_name} ({list_id}) — Found {len(tasks)} tasks")
        except Exception as e:
            print(f"❌ Error fetching tasks for list {list_id}: {str(e)}")
            tasks = []

        for task in tasks:
            try:
                raw_comments = client.get_task_comments(task.get("id")).get("comments", [])
                raw_comments = fetch_replies_for_comments(raw_comments)
                activity = client.get_task_activity(task.get("id")).get("activities", [])
                docs = build_clickup_docs(
                    task=task,
                    list_id=list_id,
                    folder_id=None,
                    space_id=space_id,
                    comments=raw_comments,
                    activity=activity,
                    list_name=list_name,
                    folder_name=None,
                    team_id=team_id
                )
                all_docs.extend(docs)
            except Exception as e:
                print(f"❌ Error processing task {task.get('id', 'unknown')}: {str(e)}")

    print(f"\n📦 Prepared {len(all_docs)} documents to store in namespace: {namespace}")
    if all_docs:
        store_documents(all_docs, namespace=namespace)
    else:
        print("❌ No documents to store.")

    return all_docs