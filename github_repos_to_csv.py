import os 
import csv
import time
import pathlib
from datetime import datetime
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

# 1) Load config from .env
load_dotenv()
USERNAME = os.getenv("GITHUB_USERNAME", "vishalsinhacodes")
TOKEN = os.getenv("GITHUB_TOKEN") # optional; inceases rate limit if set

ROOT = pathlib.Path(__file__).parent.resolve()
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# 2) Helper: Get with headers
def get(url: str) -> requests.Response:
    headers = {
        "Accept": "application/vnd.github.json",
        "User-Agent": USERNAME or "api-playground",
    }
    # If you later add a token, include it for higher rate limits
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    return requests.get(url, headers=headers, timeout=20)

# 3) Fetch all repos (handles pagination)
def fetch_all_repos(user: str) -> List[Dict[str, Any]]:
    repos: List[Dict[str, Any]] = []
    page = 1
    per_page = 100  # max allowed by GitHub

    while True:
        url = f"https://api.github.com/users/{user}/repos?per_page={per_page}&page={page}&type=owner&sort=updated"
        resp = get(url)

        if resp.status_code == 403:
            reset = resp.headers.get("x-ratelimit-reset")
            msg = "Hit rate limit. Add a GITHUB_TOKEN in .env or wait a bit."
            if reset:
                try:
                    wait_sec = max(0, int(reset) - int(time.time()))
                    msg += f" Try again in ~{wait_sec} seconds."
                except Exception:
                    pass
            raise SystemExit(f"[403] Forbidden: {msg}")

        if resp.status_code == 404:
            raise SystemExit(f"[404] User '{user}' not found.")

        if resp.status_code != 200:
            raise SystemExit(f"[{resp.status_code}] Unexpected error: {resp.text}")

        batch = resp.json()
        if not batch:
            break

        repos.extend(batch)
        page += 1

    return repos

# 4) Transform minimal fields
def simplify(repo: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": repo.get("name"),
        "full_name": repo.get("full_name"),
        "html_url": repo.get("html_url"),
        "description": (repo.get("description") or "")[:200],
        "visibility": "private" if repo.get("private") else "public",
        "language": repo.get("language"),
        "stargazers_count": repo.get("stargazers_count"),
        "forks_count": repo.get("forks_count"),
        "open_issues_count": repo.get("open_issues_count"),
        "created_at": repo.get("created_at"),
        "updated_at": repo.get("updated_at"),
        "pushed_at": repo.get("pushed_at"),
        "size_kb": repo.get("size"),
        "snapshot_date": datetime.now().strftime("%Y-%m-%d"),     
    }
    
# 5) Save to csv
def save_csv(rows: List[Dict[str, Any]], path: str) -> None:
    if not rows:
        print("No repos found. Did you push Any")
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
# 6) Pretty print top 5 by stars and recent update
def print_summaries(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No repos to summarize.")
        return
    
    # Top by stars 
    top_stars = sorted(rows, key=lambda r: r["stargazers_count"], reverse=True)[:5]
    print("\n Top 5 by Stars")
    print("------------------")    
    for r in top_stars:
        print(f"{r['stargazers_count']:>3}★  {r['name']}  → {r['html_url']}")
    
    # Most recently updated
    top_recent = sorted(rows, key=lambda r: (r["pushed_at"] or ""), reverse=True)[:5]
    print("\n Top 5 Recently Updated")
    print("--------------------------")
    for r in top_recent:
        print(f"{r['pushed_at']}  {r['name']}  → {r['html_url']}")
    
# 7) Main
if __name__ == "__main__":
    print(f"Fetching repos for : {USERNAME}")
    repos = fetch_all_repos(USERNAME)
    rows = [simplify(r) for r in repos]
    
    # Dated + latest filenames
    today = datetime.now().strftime("%Y%m%d")
    dated = DATA_DIR / f"github_repos_{USERNAME}_{today}.csv"
    latest = DATA_DIR / f"github_repos_latest.csv"

    save_csv(rows, dated)
    save_csv(rows, latest)
    
    # Keep a simple "current summary" alongside (optional helper)
    total = len(rows)
    public = sum(1 for r in rows if r["visibility"] == "public")
    stars = sum(int(r["stargazers_count"] or 0) for r in rows)
    print(f"✅ Saved GitHub snapshots: {dated.name} & github_repos_latest.csv | repos={total}, public={public}, stars={stars}")
