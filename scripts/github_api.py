import os
import requests
from typing import Dict, Any, Optional

class GitHubAPI:
    def __init__(self, token: str, repo_owner: str, repo_name: str):
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def trigger_workflow(self, url: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Trigger the download workflow with the specified m3u8 URL"""
        payload = {
            "event_type": "download-m3u8",
            "client_payload": {
                "url": url
            }
        }
        
        if name:
            payload["client_payload"]["name"] = name
            
        response = requests.post(
            f"{self.base_url}/dispatches",
            headers=self.headers,
            json=payload
        )
        
        response.raise_for_status()
        return {"status": "success", "triggered": True}
        
    def list_workflow_runs(self) -> Dict[str, Any]:
        """List recent workflow runs"""
        response = requests.get(
            f"{self.base_url}/actions/runs",
            headers=self.headers
        )
        
        response.raise_for_status()
        return response.json()
        
    def list_artifacts(self, run_id: str) -> Dict[str, Any]:
        """List artifacts for a specific workflow run"""
        response = requests.get(
            f"{self.base_url}/actions/runs/{run_id}/artifacts",
            headers=self.headers
        )
        
        response.raise_for_status()
        return response.json() 