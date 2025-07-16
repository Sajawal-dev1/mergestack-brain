import requests
from src.utils.helpers import load_env

class ClickUpClient:
    def __init__(self):
        self.env = load_env()
        self.api_key = self.env["CLICKUP_API_KEY"]
        self.base_url = "https://api.clickup.com/api/v2"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def get_teams(self):
        url = f"{self.base_url}/team"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_spaces(self, team_id):
        url = f"{self.base_url}/team/{team_id}/space"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_folders(self, space_id):
        url = f"{self.base_url}/space/{space_id}/folder"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_lists(self, folder_id):
        url = f"{self.base_url}/folder/{folder_id}/list"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_folderless_lists(self, space_id):
        # Lists not inside folders
        url = f"{self.base_url}/space/{space_id}/list"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_tasks(self, list_id):
        url = f"{self.base_url}/list/{list_id}/task"
        response = requests.get(url, headers=self.headers)
        return response.json()

    def get_task_comments(self, task_id):
        url = f"{self.base_url}/task/{task_id}/comment"
        response = requests.get(url, headers=self.headers)
        return response.json()
        
    def get_comment_thread(self, comment_id):
        url = f"{self.base_url}/comment/{comment_id}/reply"
        resp = requests.get(url, headers=self.headers)
        resp.raise_for_status()
        return resp.json().get("comments", [])     

    def get_task_activity(self, task_id):
        url = f"{self.base_url}/task/{task_id}/activity"
        response = requests.get(url, headers=self.headers)
        return response.json()
