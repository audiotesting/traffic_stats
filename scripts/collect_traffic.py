
import os
import csv
import json
import requests
from datetime import datetime, timezone
from pathlib import Path


ORG_NAME = os.environ.get("ORG_NAME", "audiotesting")
TOKEN = os.environ.get("GH_TOKEN")
BASE_URL = "https://api.github.com"
DATA_DIR = Path("data")
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get_org_repos(org: str) -> list[dict]:
    """Fetch all repositories for the organization."""
    repos = []
    page = 1
    while True:
        url = f"{BASE_URL}/orgs/{org}/repos?per_page=100&page={page}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def get_traffic_views(org: str, repo: str) -> dict:
    """Get page views and unique visitors (last 14 days, daily breakdown)."""
    url = f"{BASE_URL}/repos/{org}/{repo}/traffic/views"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 403:
        return {"count": 0, "uniques": 0, "views": []}
    response.raise_for_status()
    return response.json()


def get_traffic_clones(org: str, repo: str) -> dict:
    """Get clone counts (last 14 days, daily breakdown)."""
    url = f"{BASE_URL}/repos/{org}/{repo}/traffic/clones"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 403:
        return {"count": 0, "uniques": 0, "clones": []}
    response.raise_for_status()
    return response.json()


def get_popular_paths(org: str, repo: str) -> list[dict]:
    """Get top 10 popular content paths."""
    url = f"{BASE_URL}/repos/{org}/{repo}/traffic/popular/paths"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 403:
        return []
    response.raise_for_status()
    return response.json()


def get_referrers(org: str, repo: str) -> list[dict]:
    """Get top 10 referral sources."""
    url = f"{BASE_URL}/repos/{org}/{repo}/traffic/popular/referrers"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 403:
        return []
    response.raise_for_status()
    return response.json()


def save_daily_views(repo_name: str, views_data: dict):
    """Append daily view data to CSV, avoiding duplicates."""
    file_path = DATA_DIR / "views" / f"{repo_name}.csv"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    existing_dates = set()
    if file_path.exists():
        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_dates.add(row["date"])

    with open(file_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "views", "unique_visitors"])
        if not existing_dates:
            writer.writeheader()

        for entry in views_data.get("views", []):
            date_str = entry["timestamp"][:10]
            if date_str not in existing_dates:
                writer.writerow({
                    "date": date_str,
                    "views": entry["count"],
                    "unique_visitors": entry["uniques"],
                })


def save_daily_clones(repo_name: str, clones_data: dict):
    """Append daily clone data to CSV, avoiding duplicates."""
    file_path = DATA_DIR / "clones" / f"{repo_name}.csv"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    existing_dates = set()
    if file_path.exists():
        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_dates.add(row["date"])

    with open(file_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "clones", "unique_cloners"])
        if not existing_dates:
            writer.writeheader()

        for entry in clones_data.get("clones", []):
            date_str = entry["timestamp"][:10]
            if date_str not in existing_dates:
                writer.writerow({
                    "date": date_str,
                    "clones": entry["count"],
                    "unique_cloners": entry["uniques"],
                })


def save_summary(summary: list[dict]):
    """Save the latest collection summary as JSON."""
    file_path = DATA_DIR / "latest_summary.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(summary, f, indent=2)


def save_popular_paths(repo_name: str, paths: list[dict]):
    """Save popular paths snapshot."""
    file_path = DATA_DIR / "popular_paths" / f"{repo_name}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump({
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "paths": paths,
        }, f, indent=2)


def save_referrers(repo_name: str, referrers: list[dict]):
    """Save referrer snapshot."""
    file_path = DATA_DIR / "referrers" / f"{repo_name}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump({
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "referrers": referrers,
        }, f, indent=2)


def main():
    if not TOKEN:
        raise ValueError("GH_TOKEN environment variable is not set")

    print(f"🔍 Fetching repositories for org: {ORG_NAME}")
    repos = get_org_repos(ORG_NAME)
    print(f"📦 Found {len(repos)} repositories\n")

    summary = []
    collection_time = datetime.now(timezone.utc).isoformat()

    for repo in repos:
        repo_name = repo["name"]
        print(f"📊 Collecting traffic for: {repo_name}")

        views_data = get_traffic_views(ORG_NAME, repo_name)
        save_daily_views(repo_name, views_data)

        clones_data = get_traffic_clones(ORG_NAME, repo_name)
        save_daily_clones(repo_name, clones_data)

        paths = get_popular_paths(ORG_NAME, repo_name)
        save_popular_paths(repo_name, paths)

        referrers = get_referrers(ORG_NAME, repo_name)
        save_referrers(repo_name, referrers)

        repo_summary = {
            "repository": repo_name,
            "collected_at": collection_time,
            "views_14d_total": views_data.get("count", 0),
            "unique_visitors_14d": views_data.get("uniques", 0),
            "clones_14d_total": clones_data.get("count", 0),
            "unique_cloners_14d": clones_data.get("uniques", 0),
            "top_referrer": referrers[0]["referrer"] if referrers else "N/A",
        }
        summary.append(repo_summary)

        print(f"   Views: {repo_summary['views_14d_total']} | "
              f"Unique: {repo_summary['unique_visitors_14d']} | "
              f"Clones: {repo_summary['clones_14d_total']}")

    save_summary(summary)

    total_views = sum(s["views_14d_total"] for s in summary)
    total_uniques = sum(s["unique_visitors_14d"] for s in summary)
    total_clones = sum(s["clones_14d_total"] for s in summary)

    print(f"\n{'='*50}")
    print(f"📈 TOTALS (last 14 days)")
    print(f"   Total Views:      {total_views}")
    print(f"   Unique Visitors:  {total_uniques}")
    print(f"   Total Clones:     {total_clones}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

