from pathlib import Path

DIR_PATH = Path(__file__).parent
ROOT_PATH = DIR_PATH.parent
TEMPLATES_PATH = ROOT_PATH / "templates.json"
PROMPTS_DIR_PATH = DIR_PATH / "prompts"
STORAGE_PATH = ROOT_PATH / "output"
VIDEOS_PATH = ROOT_PATH / "videos"
PROMPT_PATH = PROMPTS_DIR_PATH / "gen.jinja"
