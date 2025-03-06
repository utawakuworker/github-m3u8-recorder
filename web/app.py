import os
import streamlit as st
import requests
from urllib.parse import urlencode
import json
import sys
import importlib
import inspect

# Add the scripts directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from github_api import GitHubAPI

# Force reload the module to ensure we have the latest version
importlib.reload(scripts.github_api)

# GitHub OAuth settings
CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")
REPO_OWNER = os.environ.get("GITHUB_REPO_OWNER")
REPO_NAME = os.environ.get("GITHUB_REPO_NAME")

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None

def authenticate():
    """Start GitHub OAuth flow"""
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": os.environ.get("REDIRECT_URI"),
        "scope": "repo workflow",
        "state": os.environ.get("OAUTH_STATE"),
    }
    auth_url = f"https://github.com/login/oauth/authorize?{urlencode(params)}"
    st.markdown(f"[Authenticate with GitHub]({auth_url})")

def handle_callback():
    """Handle OAuth callback"""
    if "code" in st.query_params:
        code = st.query_params["code"]
        response = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "code": code,
                "redirect_uri": os.environ.get("REDIRECT_URI"),
            },
            headers={"Accept": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            st.session_state.authenticated = True
            
            # Get user info
            user_response = requests.get(
                "https://api.github.com/user",
                headers={"Authorization": f"token {st.session_state.token}"}
            )
            if user_response.status_code == 200:
                st.session_state.user = user_response.json()
            
            # Clear query parameters
            st.query_params.clear()
            st.rerun()

def main():
    st.title("M3U8 Stream Recorder")
    
    # Handle OAuth callback if needed
    if not st.session_state.authenticated:
        handle_callback()
    
    # Authentication UI
    if not st.session_state.authenticated:
        st.write("Please authenticate with GitHub to use this application.")
        authenticate()
        return
    
    # User info
    st.write(f"Hello, {st.session_state.user['login']}!")
    
    # Create GitHub API client
    github_client = GitHubAPI(
        token=st.session_state.token,
        repo_owner=REPO_OWNER,
        repo_name=REPO_NAME
    )
    
    # M3U8 URL input
    st.subheader("Record Stream")
    with st.form("record_form"):
        url = st.text_input("M3U8 URL", help="Enter the full m3u8 URL of the stream you want to record")
        name = st.text_input("Recording Name (optional)", help="Give your recording a name")
        email = st.text_input("Email Address (optional)", help="Receive a notification when recording is complete")
        submitted = st.form_submit_button("Start Recording")
        
        if submitted and url:
            try:
                st.write(f"Debug - Attempting to call with URL: {url}, Name: {name}, Email: {email}")
                
                # Check the method signature to confirm it accepts email
                st.write(f"Method signature: {inspect.signature(github_client.trigger_workflow)}")
                
                result = github_client.trigger_workflow(url=url, name=name, email=email)
                st.success("Recording workflow started successfully!")
            except Exception as e:
                st.error(f"Error starting recording: {str(e)}")
                st.exception(e)  # This will show the full traceback
    
    # List recordings
    st.subheader("Your Recordings")
    if st.button("Refresh Recordings"):
        try:
            runs = github_client.list_workflow_runs()
            
            if not runs["workflow_runs"]:
                st.info("No recordings found")
            else:
                for run in runs["workflow_runs"]:
                    if run["name"] == "Download M3U8 Stream":
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.write(f"Run: {run['id']}")
                        with col2:
                            st.write(f"Status: {run['status']}")
                        with col3:
                            st.write(f"Created: {run['created_at']}")
                        
                        # Show artifacts if workflow is completed
                        if run["status"] == "completed":
                            try:
                                artifacts = github_client.list_artifacts(run["id"])
                                for artifact in artifacts["artifacts"]:
                                    st.write(f"Download: [{artifact['name']}]({artifact['archive_download_url']})")
                            except Exception as e:
                                st.error(f"Error fetching artifacts: {str(e)}")
                        
                        st.divider()
        except Exception as e:
            st.error(f"Error fetching recordings: {str(e)}")

if __name__ == "__main__":
    main() 
