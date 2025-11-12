import os
import requests
from dotenv import load_dotenv

# 1) Load environment variables (optional for future tokens)
load_dotenv()

# 2) Define the API endpoint (what are we asking for?)
username = os.getenv("GITHUB_USERNAME", "vishalsinhacodes")
url = f"https://api.github.com/users/{username}"

# 3) Make the HTTP GET request
response = requests.get(url)

# 4) Check basic status (200 = OK)
print(f"Status: {response.status_code}")
if response.status_code != 200:
    print("Something went wrong. Respone text:")
    print(response.text)
    raise SystemExit()

# 5) Parse JSON into a Python dict
data = response.json()

# 6) Extract a few useful fields
login = data.get("login")
name = data.get("name")
public_repos = data.get("public_repos")
followers = data.get("followers")
following = data.get("following")
profile = data.get("html_url")

# 7) Print a human-friendly summary
print("\nGithub User Summary")
print("---------------------")
print(f"Login:         {login}")
print(f"Name:          {name}")
print(f"Public repos:  {public_repos}")
print(f"Followers:     {followers}")
print(f"Following:     {following}")
print(f"Profile link:  {profile}")