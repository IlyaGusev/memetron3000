import json
from datetime import datetime, timedelta
from typing import Dict
from collections import Counter, deque

import requests
from tqdm import tqdm

from genmeme.db import SessionLocal, ImageRecord

URL = "https://aimemearena-676a343606c3.herokuapp.com/api/battles"

db = SessionLocal()
all_records = list(db.query(ImageRecord).order_by(ImageRecord.created_at.asc()).all())
all_records.sort(key=lambda x: x.created_at)

global_wins_count = 0
global_ties_count = 0
global_bad_ties_count = 0
global_lose_count = 0
template_win_counts: Dict[str, int] = Counter()
template_lose_counts: Dict[str, int] = Counter()
template_tie_counts: Dict[str, int] = Counter()
template_bad_tie_counts: Dict[str, int] = Counter()
lose_examples = deque(maxlen=10)

curent_timestamp = datetime.utcnow()
for r in tqdm(all_records):
    result_id = int(r.result_id)
    if result_id > 12345678:
        continue
    timestamp = r.created_at
    image_url = r.image_url
    template = image_url.split("/")[4]
    label = "UNDEFINED"
    if r.label in ("WIN", "TIE", "TIE_BAD", "LOSE"):
        label = r.label
    elif curent_timestamp < timestamp + timedelta(hours=2):
        url = URL + f"?result_id={result_id}"
        response = requests.get(url)
        items = response.json()["items"]
        if not items:
            continue
        is_first = items[0]["result_1_id"] == result_id
        vote = items[0]["vote"]
        if is_first and vote == "FIRST" or not is_first and vote == "SECOND":
            label = "WIN"
        elif vote == "SAME":
            label = "TIE"
        elif vote == "SAME_SHIT":
            label = "TIE_BAD"
        else:
            label = "LOSE"
    else:
        print(f"Skipping {timestamp}")

    if label == "WIN":
        global_wins_count += 1
        template_win_counts[template] += 1
    elif label == "TIE":
        global_ties_count += 1
        template_tie_counts[template] += 1
    elif label == "TIE_BAD":
        global_bad_ties_count += 1
        template_bad_tie_counts[template] += 1
        if r.query:
            lose_examples.append(r)
    elif label == "LOSE":
        global_lose_count += 1
        template_lose_counts[template] += 1
        if r.query:
            lose_examples.append(r)

    if r.label not in ("WIN", "TIE", "TIE_BAD", "LOSE") and label != "UNDEFINED":
        r.label = label
        db.commit()

with open("templates.json") as f:
    templates = [t["id"] for t in json.load(f)]

print(f"GLOBAL WINS: {global_wins_count}")
print(f"GLOBAL LOSES: {global_lose_count}")
print(f"GLOBAL TIES: {global_ties_count}")
print(f"GLOBAL BAD TIES: {global_bad_ties_count}")
used_templates = list(
    (set(template_win_counts.keys()) | set(template_lose_counts.keys()))
    & set(templates)
)
template_win_rates = dict()
for template in used_templates:
    wins = template_win_counts[template]
    loses = template_lose_counts[template]
    ties = template_tie_counts[template]
    bad_ties = template_bad_tie_counts[template]
    template_win_rates[template] = (
        wins / (wins + loses),
        (wins + ties) / (wins + loses + ties + bad_ties),
        wins + loses,
        wins + loses + ties + bad_ties,
    )

for name, (winrate, tie_winrate, count, count_w_ties) in sorted(
    template_win_rates.items(), key=lambda x: x[1]
):
    if count < 3:
        continue
    print(f"{name: <30}{count: <5}{count_w_ties: <5}{winrate:.2f}   {tie_winrate:.2f}")


print()
print("LOSE examples:")
for r in lose_examples:
    if r.query is None:
        continue
    query = r.query.replace("\n", " ")
    meme = r.image_url.replace("\n", " ")
    print(f"PROMPT: {query}, MEME: {meme}, URL: {r.public_url}")

db.close()
