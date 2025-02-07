import json
from collections import Counter

import requests
from tqdm import tqdm

from genmeme.db import SessionLocal, ImageRecord

URL = "https://aimemearena-676a343606c3.herokuapp.com/api/battles"

db = SessionLocal()
all_records = list(db.query(ImageRecord).all())
db.close()

global_wins_count = 0
global_ties_count = 0
global_bad_ties_count = 0
global_lose_count = 0
template_win_counts = Counter()
template_lose_counts = Counter()
template_tie_counts = Counter()
template_bad_tie_counts = Counter()

for r in tqdm(all_records[-2000:]):
    result_id = int(r.result_id)
    image_url = r.image_url
    template = image_url.split("/")[4]
    url = URL + f"?result_id={result_id}"
    response = requests.get(url)
    items = response.json()["items"]
    if not items:
        continue
    is_first = items[0]["result_1_id"] == result_id
    vote = items[0]["vote"]
    if is_first and vote == "FIRST" or not is_first and vote == "SECOND":
        global_wins_count += 1
        template_win_counts[template] += 1
    elif vote == "SAME":
        global_ties_count += 1
        template_tie_counts[template] += 1
    elif vote == "SAME_SHIT":
        global_bad_ties_count += 1
        template_bad_tie_counts[template] += 1
    else:
        global_lose_count += 1
        template_lose_counts[template] += 1

with open("templates.json") as r:
    templates = [t["id"] for t in json.load(r)]

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
