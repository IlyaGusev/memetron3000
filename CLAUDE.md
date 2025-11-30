# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MEMETRON 3000 is an automatic Russian meme generator that uses language models to generate memes based on predefined templates. The system accepts text prompts and generates contextually appropriate memes using vision-capable LLMs (via OpenRouter API with Google's Gemini 3 Pro Image).

## Setup and Installation

### Initial Setup
```bash
bash download.sh  # Downloads videos and meme templates
pip3 install -r requirements.txt
```

Or use uv (preferred):
```bash
uv sync
```

### Running the Server
```bash
OPENROUTER_API_KEY=<your_key> uv run -m genmeme.server
```

The server runs on port 8081 by default. Use `--port` and `--host` flags to customize.

## Development Commands

### Code Quality
```bash
make black      # Format code with black
make validate   # Run black, flake8, and mypy (strict mode)
```

### Manual Validation Steps
```bash
black genmeme
flake8 genmeme
mypy genmeme --strict --explicit-package-bases
```

## Architecture

### Core Components

**genmeme/server.py** - FastAPI web server that exposes the meme generation API
- Endpoint: `POST /api/v1/predict` - accepts prompt and optional template ID
- Endpoint: `GET /health` - health check endpoint
- Handles retries (3 attempts) for meme generation
- Records all generated memes in SQLite database
- Serves generated output via `/output` static files

**genmeme/gen.py** - Core meme generation logic
- `generate_meme()` - Main async function that orchestrates meme creation
- Randomly selects templates from templates.json (2 by default)
- Renders Jinja2 prompt template with query and template metadata
- Calls LLM to generate meme based on selected template images

**genmeme/llm.py** - LLM integration layer
- `openrouter_nano_banana_generate()` - Async function to call OpenRouter API
- Uses vision-capable models (default: `google/gemini-3-pro-image-preview`)
- Encodes template images as base64 and sends with text prompt
- Extracts generated image from response and saves to output directory

**genmeme/db.py** - SQLAlchemy database models
- `ImageRecord` - Stores metadata for generated memes (query, URL, template ID, timestamp)
- Uses SQLite database (`images.db` in project root)

**genmeme/files.py** - Path constants
- Defines standard locations for templates, prompts, storage, and images

### Data Flow

1. User sends POST request with text prompt to `/api/v1/predict`
2. Server selects random meme templates from `templates.json`
3. Template images are loaded from `images/` directory
4. Jinja2 prompt from `genmeme/prompts/gen.jinja` is rendered with query and template info
5. Rendered prompt + template images sent to LLM via OpenRouter
6. LLM generates meme image based on the prompt and templates
7. Generated image saved to `output/` directory with UUID filename
8. Metadata recorded in SQLite database
9. Public URL returned to client

### Key Files and Directories

- `templates.json` - Meme template definitions with Russian descriptions and examples
- `images/` - Template images referenced by template IDs
- `output/` - Generated meme outputs (served statically)
- `genmeme/prompts/gen.jinja` - Jinja2 template for generating LLM prompts
- `images.db` - SQLite database storing generation metadata

## Configuration

Environment variables:
- `OPENROUTER_API_KEY` - Required for LLM API calls
- `PROMPT_PATH` - Override default prompt template path
- `TEMPLATES_PATH` - Override default templates.json path

## Type Checking

The codebase uses strict mypy type checking. All code must pass:
```bash
mypy genmeme --strict --explicit-package-bases
```

Note: Some dependencies (like `fire`) use `# type: ignore` comments where type stubs are unavailable.

## Code Style

### Comments
- **Do not write obvious code comments.** Code should be self-explanatory through clear variable names and function names.
- **Only write comments when explaining complex logic** that isn't immediately clear from the code itself.
- Examples of what NOT to comment:
  ```python
  # Bad: obvious comment
  user_count = len(users)  # Get the count of users

  # Good: self-explanatory code, no comment needed
  user_count = len(users)
  ```
- Examples of when TO comment:
  ```python
  # Good: explains non-obvious algorithm or business logic
  # Use binary search because the list is pre-sorted by timestamp
  index = bisect_left(timestamps, target_time)
  ```

## Russian Language Context

This project generates memes in Russian. The templates in `templates.json` contain:
- Russian descriptions (`description` field)
- Russian example captions (`query_examples` with `captions`)
- Template metadata for meme formats popular in Russian internet culture
