import json
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Deque
from collections import Counter, deque, defaultdict

import requests
import fire  # type: ignore
from tqdm import tqdm

from genmeme.db import SessionLocal, ImageRecord

URL = "https://aimemearena-676a343606c3.herokuapp.com/api/battles"
TEMPLATES_PATH = "templates.json"


def get_stats(nrows: Optional[int] = None, refresh_hours: int = 48) -> None:
    db = SessionLocal()
    all_records = list(
        db.query(ImageRecord).order_by(ImageRecord.created_at.asc()).all()
    )
    all_records.sort(key=lambda x: x.created_at)
    with open(TEMPLATES_PATH) as f:
        templates = {t["id"]: t for t in json.load(f)}

    global_wins_count = 0
    global_ties_count = 0
    global_bad_ties_count = 0
    global_lose_count = 0
    template_win_counts: Dict[str, int] = Counter()
    template_lose_counts: Dict[str, int] = Counter()
    template_tie_counts: Dict[str, int] = Counter()
    template_bad_tie_counts: Dict[str, int] = Counter()
    lose_examples: Deque[Any] = deque(maxlen=20)
    win_examples: Deque[Any] = deque(maxlen=20)
    template_win_examples = defaultdict(list)

    curent_timestamp = datetime.utcnow()
    used_templates = set()
    if nrows:
        all_records = all_records[-nrows:]
    for r in tqdm(all_records):
        result_id = int(r.result_id)
        timestamp = r.created_at
        image_url = r.image_url
        template = image_url.split("/")[4]
        used_templates.add(template)
        label = "UNDEFINED"
        if r.label in ("WIN", "TIE", "TIE_BAD", "LOSE"):
            label = r.label
        elif curent_timestamp < timestamp + timedelta(hours=refresh_hours):
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

        if label == "WIN":
            global_wins_count += 1
            template_win_counts[template] += 1
            win_examples.append(r)
            if template in templates:
                template_win_examples[template].append(r)
        elif label == "TIE":
            global_ties_count += 1
            template_tie_counts[template] += 1
            win_examples.append(r)
            if template in templates:
                template_win_examples[template].append(r)
        elif label == "TIE_BAD":
            global_bad_ties_count += 1
            template_bad_tie_counts[template] += 1
            lose_examples.append(r)
        elif label == "LOSE":
            global_lose_count += 1
            template_lose_counts[template] += 1
            lose_examples.append(r)

        if r.label not in ("WIN", "TIE", "TIE_BAD", "LOSE") and label != "UNDEFINED":
            r.label = label
            db.commit()

    print(f"GLOBAL WINS: {global_wins_count}")
    print(f"GLOBAL LOSES: {global_lose_count}")
    print(f"GLOBAL TIES: {global_ties_count}")
    print(f"GLOBAL BAD TIES: {global_bad_ties_count}")

    current_templates = set(templates.keys())
    used_templates = (used_templates & current_templates) | current_templates

    template_win_rates = dict()
    for template in used_templates:
        wins = template_win_counts[template]
        loses = template_lose_counts[template]
        ties = template_tie_counts[template]
        bad_ties = template_bad_tie_counts[template]
        all_count = wins + loses + ties + bad_ties
        true_winrate = (wins + ties) / all_count if all_count != 0 else 0
        template_win_rates[template] = (
            true_winrate,
            wins / (wins + loses) if wins + loses != 0 else 0,
            wins + loses,
            wins + loses + ties + bad_ties,
        )

    for name, (tie_winrate, winrate, count, count_w_ties) in sorted(
        template_win_rates.items(), key=lambda x: x[1]
    ):
        print(
            f"{name: <30}{count_w_ties: <10}{count: <10}{tie_winrate:.2f}   {winrate:.2f}"
        )

    print()
    print("WIN examples:")
    for r in win_examples:
        if r.query is None:
            continue
        query = r.query.replace("\n", " ")
        meme = r.image_url.replace("\n", " ")
        print(
            f"TS: {r.created_at}, PROMPT: {query}, TEMPLATE: {r.template_id}, CAPTIONS: {r.captions}, URL: {r.public_url}"
        )

    print()
    print("LOSE examples:")
    for r in lose_examples:
        if r.query is None:
            continue
        query = r.query.replace("\n", " ")
        meme = r.image_url.replace("\n", " ")
        print(
            f"TS: {r.created_at}, PROMPT: {query}, TEMPLATE: {r.template_id}, CAPTIONS: {r.captions}, URL: {r.public_url}"
        )

    if False:
        for template, examples in template_win_examples.items():
            print()
            print(template)
            for r in examples[-5:]:
                if not r.query:
                    continue
                query = r.query.replace("\n", " ")
                captions = r.image_url.replace("\n", " ").split("/")[5:]
                meme = str([c.replace("_", " ") for c in captions])
                print(f"PROMPT: {query}, MEME: {meme}, URL: {r.public_url}")

    db.close()


if __name__ == "__main__":
    fire.Fire(get_stats)
