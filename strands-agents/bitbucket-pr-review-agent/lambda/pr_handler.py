import requests
import json

# replace this with your bitbucket access token
ACCESS_TOKEN = "<Bitbucket API Key or Access token>"

# This is bitbucket cloud API endpoint
API_URL = 'https://api.bitbucket.org/2.0/'


class PullRequestHandler:
    def __init__(self, project_name: str, repo_name: str, pull_request_id: int):
        self.project_name = project_name
        self.repo_name = repo_name
        self.pull_request_id = pull_request_id
        self.request_headers = {
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json"                    
                    }

    def find_diff(self):
        url = f"{API_URL}repositories/{self.project_name}/{self.repo_name}/pullrequests/{self.pull_request_id}/diff"
        response = requests.request("GET", url,headers=self.request_headers)
        return response.text

    def decline(self):
        url = f"{API_URL}repositories/{self.project_name}/{self.repo_name}/pullrequests/{self.pull_request_id}/decline"
        response = requests.request("POST", url, headers=self.request_headers)
        return response.text

    def approve(self):
        #url = f"{API_URL}repositories/{self.project_name}/{self.repo_name}/pullrequests/{self.pull_request_id}/approve"
        url = f"https://api.bitbucket.org/2.0/repositories/{self.project_name}/{self.repo_name}/pullrequests/{self.pull_request_id}/approve"

        response = requests.post(url, headers=self.request_headers)
        return response
    
    def merge(self, message: str):
        url = f"{API_URL}repositories/{self.project_name}/{self.repo_name}/pullrequests/{self.pull_request_id}/merge"

        payload = json.dumps( {
                                "type": "pullrequest",
                                "message": message,
                                "close_source_branch": True,
                                "merge_strategy": "merge_commit"
                                } )

        response = requests.post(url, headers=self.request_headers, data=payload)
        return response.text

    def add_comment(self, comments: str):
        url = f"{API_URL}repositories/{self.project_name}/{self.repo_name}/pullrequests/{self.pull_request_id}/comments"
        payload = {
            "content": {
                "raw": comments
            }
        }
        response = requests.post(url, headers=self.request_headers, data=json.dumps(payload))
        return response.text

    


