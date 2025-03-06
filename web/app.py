import os
import streamlit as st
import requests
from urllib.parse import urlencode
import json
import sys
import inspect
import re

# Add the scripts directory to the Python path
scripts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts')
sys.path.append(scripts_dir)

# Import from the directory we added to path
from github_api import GitHubAPI  # Not scripts.github_api

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

def is_youtube_url(url: str) -> bool:
    """Check if a URL is a YouTube URL"""
    youtube_patterns = [
        r"^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$",
        r"^(https?\:\/\/)?(www\.)?youtube\.com\/watch\?v=.+$",
        r"^(https?\:\/\/)?(www\.)?youtu\.be\/.+$"
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)

def is_m3u8_url(url: str) -> bool:
    """Check if a URL is an M3U8 URL"""
    return url.lower().endswith('.m3u8') or '.m3u8' in url.lower()

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
    
    # M3U8/YouTube URL input
    st.subheader("Record Stream or Download Video")
    with st.form("record_form"):
        url = st.text_input("Video URL", help="Enter an M3U8 stream URL or YouTube video URL")
        name = st.text_input("Recording Name (optional)", help="Give your recording a name")
        email = st.text_input("Email Address (optional)", help="Receive a notification when recording is complete")
        
        # Show YouTube-specific options if it looks like a YouTube URL
        youtube_options = False
        if url and is_youtube_url(url):
            youtube_options = True
            is_live = st.checkbox("This is a live stream", help="Check this if you're recording a YouTube live stream")
            st.info("YouTube live streams will be recorded from the beginning using the --live-from-start option.")
        
        submitted = st.form_submit_button("Start Recording")
        
        if submitted and url:
            try:
                # Detect URL type
                is_youtube = is_youtube_url(url)
                
                # Only pass is_live if it's a YouTube URL
                if is_youtube:
                    result = github_client.trigger_workflow(
                        url=url, 
                        name=name, 
                        email=email, 
                        is_youtube=True,
                        is_live=is_live if youtube_options else False
                    )
                else:
                    result = github_client.trigger_workflow(
                        url=url, 
                        name=name, 
                        email=email
                    )
                    
                st.success(f"{'YouTube download' if is_youtube else 'M3U8 recording'} started successfully!")
            except Exception as e:
                st.error(f"Error starting recording: {str(e)}")
    
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
