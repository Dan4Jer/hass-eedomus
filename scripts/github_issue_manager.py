#!/usr/bin/env python3
"""
GitHub Issue Manager for hass-eedomus

This script provides functionality to:
- List open issues
- Add comments to issues
- Update issues
- Close issues

Requires: requests library
"""

import requests
import json
import sys
import subprocess
from typing import List, Dict, Optional

# Configuration
REPO_OWNER = "Dan4Jer"
REPO_NAME = "hass-eedomus"

# Essayez de lire le token depuis le fichier .git-credentials
try:
    import os
    with open(os.path.expanduser("~/.git-credentials")) as f:
        for line in f:
            if "github.com" in line:
                # Extract token from URL format: https://user:token@github.com
                parts = line.split(":")
                if len(parts) >= 3:
                    GITHUB_TOKEN = parts[2].split("@")[0]
                else:
                    GITHUB_TOKEN = parts[1].split("@")[0]
                break
        else:
            GITHUB_TOKEN = None
except:
    GITHUB_TOKEN = None

if not GITHUB_TOKEN:
    print("⚠️  Avertissement: Aucun token GitHub trouvé dans la configuration")
    print("Utilisez 'git config' ou ~/.git-credentials pour configurer le token")
    sys.exit(1)

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}


def make_github_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
    """Make a request to GitHub API."""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/{endpoint}"
    
    if method.upper() == "GET":
        response = requests.get(url, headers=HEADERS)
    elif method.upper() == "POST":
        response = requests.post(url, headers=HEADERS, json=data)
    elif method.upper() == "PATCH":
        response = requests.patch(url, headers=HEADERS, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")
    
    if response.status_code == 200 or response.status_code == 201:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")
        return {}


def list_open_issues() -> List[Dict]:
    """List all open issues."""
    return make_github_request("GET", "issues?state=open")


def get_issue(issue_number: int) -> Dict:
    """Get a specific issue."""
    return make_github_request("GET", f"issues/{issue_number}")


def add_comment(issue_number: int, comment: str) -> Dict:
    """Add a comment to an issue."""
    endpoint = f"issues/{issue_number}/comments"
    data = {"body": comment}
    return make_github_request("POST", endpoint, data)


def update_issue(issue_number: int, title: Optional[str] = None, body: Optional[str] = None, state: Optional[str] = None) -> Dict:
    """Update an issue."""
    endpoint = f"issues/{issue_number}"
    data = {}
    if title:
        data["title"] = title
    if body:
        data["body"] = body
    if state:
        data["state"] = state
    
    if not data:
        print("No data provided for update")
        return {}
    
    return make_github_request("PATCH", endpoint, data)


def close_issue(issue_number: int) -> Dict:
    """Close an issue."""
    return update_issue(issue_number, state="closed")


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python github_issue_manager.py <command> [args]")
        print("Commands:")
        print("  list - List all open issues")
        print("  comment <issue#> <comment> - Add comment to issue")
        print("  close <issue#> - Close an issue")
        print("  get <issue#> - Get issue details")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        print("Listing open issues...")
        issues = list_open_issues()
        if issues:
            print(f"Found {len(issues)} open issues:")
            for issue in issues:
                print(f"#{issue['number']}: {issue['title']}")
                print(f"  Created: {issue['created_at']}")
                print(f"  URL: {issue['html_url']}")
                print()
        else:
            print("No open issues found.")
    
    elif command == "comment" and len(sys.argv) >= 4:
        issue_number = int(sys.argv[2])
        comment = " ".join(sys.argv[3:])
        print(f"Adding comment to issue #{issue_number}...")
        result = add_comment(issue_number, comment)
        if result:
            print(f"Comment added successfully!")
            print(f"URL: {result.get('html_url', 'Unknown')}")
        else:
            print("Failed to add comment.")
    
    elif command == "close" and len(sys.argv) >= 3:
        issue_number = int(sys.argv[2])
        print(f"Closing issue #{issue_number}...")
        result = close_issue(issue_number)
        if result:
            print(f"Issue closed successfully!")
            print(f"State: {result.get('state', 'Unknown')}")
        else:
            print("Failed to close issue.")
    
    elif command == "get" and len(sys.argv) >= 3:
        issue_number = int(sys.argv[2])
        print(f"Getting issue #{issue_number}...")
        issue = get_issue(issue_number)
        if issue:
            print(f"Issue #{issue['number']}: {issue['title']}")
            print(f"State: {issue['state']}")
            print(f"Created: {issue['created_at']}")
            print(f"URL: {issue['html_url']}")
            print(f"\nBody:\n{issue['body']}")
        else:
            print("Failed to get issue.")
    
    else:
        print(f"Unknown command: {command}")
        print("Usage: python github_issue_manager.py <command> [args]")


if __name__ == "__main__":
    main()
