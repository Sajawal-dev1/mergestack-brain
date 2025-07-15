from src.clickup.client import ClickUpClient
from src.clickup.ingest import ingest_clickup_tasks

def ingest_all_clickup_data():
    client = ClickUpClient()

    # Step 1: Get all teams
    teams = client.get_teams().get("teams", [])
    if not teams:
        print("❌ No teams found.")
        return

    for team in teams:
        team_id = team["id"]
        team_name = team["name"]
        print(f"\n🧠 Processing Team: {team_name} ({team_id})")

        # Step 2: Get all spaces in this team
        spaces = client.get_spaces(team_id).get("spaces", [])
        if not spaces:
            print(f"⚠️ No spaces found in team: {team_name}")
            continue

        for space in spaces:
            space_id = space["id"]
            space_name = space["name"]
            print(f"\n📦 Ingesting Space: {space_name} ({space_id})")

            namespace = f"team-{team_id}-space-{space_id}"
            try:
                ingest_clickup_tasks(team_id, space_id, namespace=namespace)
                print(f"✅ Finished storing tasks in namespace: {namespace}")
            except Exception as e:
                print(f"❌ Error while processing space {space_name}: {str(e)}")

if __name__ == "__main__":
    ingest_all_clickup_data()
