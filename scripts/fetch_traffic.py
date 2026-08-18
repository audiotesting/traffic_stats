
import os
import json
import requests
from datetime import datetime

GH_TOKEN = os.environ["TRAFFIC_PAT"]
USERNAME = "audiotesting"

REPOS = [
    "keyboards3",
    "keyboardsESP",
    "keyboardsIT",
    "keyboardsPL",
    "keyboardsSK",
    "keyboardsUA",
    "mice",
    "miceESP",
    "miceITA",
    "micePOL",
    "miceSVK",
    "miceUA",
    "headphones",
    "Headphones-ES",
    "Headphones-IT",
    "Headphones-PL",
    "Headphones-SK",
    "Headphones-UA"
]

HEADERS = {
    "Authorization": f"Bearer {GH_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

OUTPUT_DIR = "data"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def fetch_views(repo):
    url = f"https://api.github.com/repos/{USERNAME}/{repo}/traffic/views"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    print(f"Error {response.status_code} for {repo}: {response.text}")
    return None


def load_history(repo):
    history_file = os.path.join(OUTPUT_DIR, f"{repo}_history.json")
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            return json.load(f)
    return {"repo": repo, "total_views": 0, "total_uniques": 0, "daily": {}}


def save_history(repo, history):
    history_file = os.path.join(OUTPUT_DIR, f"{repo}_history.json")
    with open(history_file, "w") as f:
        json.dump(history, f, indent=2)


def main():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    summary = []

    print(f"Fetching traffic stats - {today}")
    print("=" * 50)

    for repo in REPOS:
        print(f"Fetching: {repo}...")
        views_data = fetch_views(repo)
        if not views_data:
            continue

        history = load_history(repo)

        for day in views_data.get("views", []):
            date_key = day["timestamp"][:10]
            history["daily"][date_key] = {
                "views": day["count"],
                "uniques": day["uniques"],
            }

        history["total_views"] = sum(d["views"] for d in history["daily"].values())
        history["total_uniques"] = sum(d["uniques"] for d in history["daily"].values())

        save_history(repo, history)

        summary.append({
            "repo": repo,
            "total_views": history["total_views"],
            "total_uniques": history["total_uniques"],
            "days_tracked": len(history["daily"]),
        })

        print(f"  Views: {history['total_views']} | Uniques: {history['total_uniques']}")

    summary_file = os.path.join(OUTPUT_DIR, "summary.json")
    with open(summary_file, "w") as f:
        json.dump({"last_updated": today, "repos": summary}, f, indent=2)

    print(f"\nDone! Updated stats for {len(summary)} repos.")


if __name__ == "__main__":
    main()

