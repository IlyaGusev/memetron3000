import json
from collections import Counter

import requests

from genmeme.db import SessionLocal, ImageRecord

URL = "https://aimemearena-676a343606c3.herokuapp.com/api/battles"

db = SessionLocal()
all_records = db.query(ImageRecord).all()
db.close()

global_wins_count = 0
global_ties_count = 0
global_lose_count = 0
template_win_counts = Counter()
template_lose_counts = Counter()

for r in all_records:
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
    elif vote in ("SAME_SHIT", "SAME"):
        global_ties_count += 1
    else:
        template_lose_counts[template] += 1
        global_lose_count += 1

with open("templates.json") as r:
    templates = [t["id"] for t in json.load(r)]

print(f"GLOBAL WINS: {global_wins_count}")
print(f"GLOBAL LOSES: {global_lose_count}")
print(f"GLOBAL TIES: {global_ties_count}")
used_templates = list(
    (set(template_win_counts.keys()) | set(template_lose_counts.keys())) & set(templates)
)
template_win_rates = dict()
for template in used_templates:
    template_win_rates[template] = (template_win_counts[template] / (
        template_win_counts[template] + template_lose_counts[template]
    ), template_win_counts[template] + template_lose_counts[template])

for name, (winrate, count) in sorted(template_win_rates.items(), key=lambda x: x[1]):
    if count < 5:
        continue
    print(name, count, winrate)
