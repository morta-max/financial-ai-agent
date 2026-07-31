"""Create GitHub repository and push code."""
import os
import subprocess
import sys

# Read token from file
token_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".github_token")
with open(token_file) as f:
    token = f.read().strip()

import urllib.request
import json

# Create repo
print("Creating GitHub repository...")
data = json.dumps({
    "name": "financial-ai-agent",
    "description": "AI-powered financial research and stock analysis platform for Chinese A-shares",
    "private": False
}).encode()

req = urllib.request.Request(
    "https://api.github.com/user/repos",
    data=data,
    headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
        print(f"  Created: {result.get('html_url', 'already exists?')}")
except urllib.error.HTTPError as e:
    body = e.read().decode()
    if "already exists" in body or e.code == 422:
        print("  Repository already exists, continuing...")
    else:
        print(f"  Error: {e.code} - {body}")
        sys.exit(1)

# Push
print("Pushing to GitHub...")
repo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# Set remote with credentials for push
remote_url = f"https://mortal:{token}@github.com/morta-max/financial-ai-agent.git"
subprocess.run(["git", "-C", repo_dir, "remote", "set-url", "origin", remote_url], check=True)

# Push
subprocess.run(["git", "-C", repo_dir, "push", "-u", "origin", "master"], check=True)

# Reset remote to clean URL (no token)
subprocess.run(["git", "-C", repo_dir, "remote", "set-url", "origin", "https://github.com/morta-max/financial-ai-agent.git"], check=True)

print("Done! https://github.com/morta-max/financial-ai-agent")
