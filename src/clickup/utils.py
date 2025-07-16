# src/clickup/utils.py
from src.clickup.client import ClickUpClient

def get_all_namespaces():
    client = ClickUpClient()
    namespaces = []

    teams = client.get_teams().get("teams", [])
    for team in teams:
        team_id = team["id"]
        team_name = team["name"]

        spaces = client.get_spaces(team_id).get("spaces", [])
        for space in spaces:
            space_id = space["id"]
            space_name = space["name"]

            namespace = f"team-{team_id}-space-{space_id}"
            namespaces.append({
                "team_name": team_name,
                "space_name": space_name,
                "namespace": namespace
            })

    return namespaces
