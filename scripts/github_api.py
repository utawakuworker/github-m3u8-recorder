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
    
    def trigger_workflow(self, url: str, name: Optional[str] = None, email: Optional[str] = None,
                         is_youtube: bool = False, is_live: bool = False) -> Dict[str, Any]:
        """Trigger the download workflow with the specified URL"""
        print(f"Debug - URL: {url}, Name: {name}, Email: {email}, IsYoutube: {is_youtube}, IsLive: {is_live}")
        
        payload = {
            "event_type": "download-m3u8",
            "client_payload": {
                "url": url,
                "is_youtube": is_youtube,
                "is_live": is_live
            }
        }
        
        if name:
            payload["client_payload"]["name"] = name
            
        if email:
            payload["client_payload"]["email"] = email
        
        print(f"Debug - Payload: {payload}")
        
        response = requests.post(
            f"{self.base_url}/dispatches",
            headers=self.headers,
            json=payload
        )
        
        response.raise_for_status()
        return {"status": "success", "triggered": True}
        
    def list_workflow_runs(self) -> Dict[str, Any]:
        """List recent workflow runs for the recording workflow"""
        # Get runs specifically for our workflow file
        response = requests.get(
            f"{self.base_url}/actions/workflows/download_m3u8.yml/runs",
            headers=self.headers,
            params={"per_page": 30}
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
