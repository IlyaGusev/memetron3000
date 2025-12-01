# MEMETRON 3000

An automatic Russian meme generator powered by vision-capable language models. MEMETRON 3000 uses AI to generate contextually appropriate memes based on text prompts and predefined meme templates.

## Features

- **AI-Powered Generation**: Uses Google's Gemini 3 Pro Image via OpenRouter to generate memes
- **Template-Based**: 100+ Russian meme templates with descriptions and examples
- **Queue System**: Async job queue for handling multiple generation requests
- **Gallery**: Browse all previously generated memes with pagination
- **Thumbnail Generation**: Automatic thumbnail creation for fast loading
- **REST API**: Full-featured API for programmatic access
- **Web Interface**: Clean, modern web UI for generating and browsing memes

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager (recommended) or pip
- OpenRouter API key (for meme generation)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/IlyaGusev/memetron3000.git
cd memetron3000
```

2. Download meme template images:
```bash
bash download.sh
```

3. Install dependencies:
```bash
# Using uv (recommended)
uv sync

# Or using pip
pip3 install -e .
```

4. Configure environment variables in `.env` file:
   - Set your `OPENROUTER_API_KEY` (get it from [OpenRouter](https://openrouter.ai/))
   - Set `ENABLE_GENERATION=true` to enable meme generation

## Configuration

Configure the application using environment variables:

- `OPENROUTER_API_KEY` - **Required** for meme generation. Get your key from [OpenRouter](https://openrouter.ai/)
- `ENABLE_GENERATION` - Enable/disable meme generation (default: `"false"`). Set to `"true"` to allow generation
- `PROMPT_PATH` - Override default prompt template path (default: `genmeme/prompts/gen.jinja`)
- `TEMPLATES_PATH` - Override default templates.json path (default: `templates.json`)

## Running the Server

Start the server with:
```bash
uv run -m genmeme.server
```

The server will start on `http://localhost:8090` by default.

### Command-line Options

```bash
# Custom port and host
uv run -m genmeme.server --port 8081 --host 0.0.0.0
```

## API Documentation

### Generate Meme

**POST** `/api/v1/predict`

Submit a meme generation request. Returns a job ID for tracking progress.

Request body:
```json
{
  "prompt": "Your meme prompt in Russian",
  "selected_template_id": "bender"  // Optional, random if not specified
}
```

Response:
```json
{
  "job_id": "uuid",
  "position": 1
}
```

### Check Job Status

**GET** `/api/v1/job/{job_id}`

Check the status of a meme generation job.

Response:
```json
{
  "job_id": "uuid",
  "status": "completed",  // queued, processing, completed, or failed
  "position": 0,
  "created_at": "2025-12-01T12:00:00Z",
  "started_at": "2025-12-01T12:00:05Z",
  "completed_at": "2025-12-01T12:00:15Z",
  "result_url": "output/filename.jpg",
  "error": null
}
```

### Get Templates

**GET** `/api/v1/templates`

Get a list of all available meme templates.

Response:
```json
[
  {
    "id": "bender",
    "name": "I'm Going to Build My Own Theme Park",
    "description": "Кадр из мультсериала 'Футурама'..."
  }
]
```

### Gallery

**GET** `/api/v1/gallery?page=1&page_size=24`

Get paginated list of previously generated memes.

Query parameters:
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 24, max: 100)

Response:
```json
{
  "memes": [
    {
      "result_id": "uuid",
      "public_url": "output/uuid.jpg",
      "thumbnail_url": "output/thumbnails/uuid.jpg",
      "query": "Original prompt",
      "created_at": "2025-12-01T12:00:00Z",
      "template_ids": "bender,bilbo"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 24,
  "total_pages": 5
}
```

### Queue Size

**GET** `/api/v1/queue/size`

Get the current queue size.

### Configuration

**GET** `/api/v1/config`

Get server configuration (e.g., whether generation is enabled).

### Health Check

**GET** `/health`

Health check endpoint for monitoring.

## Architecture

### Components

- **server.py** - FastAPI web server with job queue management
- **gen.py** - Core meme generation logic and template selection
- **llm.py** - OpenRouter API integration for AI-powered image generation
- **db.py** - SQLAlchemy models for storing meme metadata
- **queue.py** - Async job queue system for handling generation requests
- **thumbnails.py** - Image thumbnail generation using Pillow
- **files.py** - Path constants and configuration

### Data Flow

1. User submits prompt via web UI or API
2. Server creates a job and adds it to the async queue
3. Queue worker picks up the job and starts processing
4. Random meme templates are selected (or specific template if requested)
5. Jinja2 prompt template is rendered with user query and template metadata
6. Prompt + template images sent to LLM via OpenRouter
7. LLM generates new meme image based on the prompt
8. Generated image is saved to `output/` directory
9. Thumbnail is created and saved to `output/thumbnails/`
10. Metadata is stored in SQLite database
11. Job status is updated with result URL
12. User can retrieve the generated meme

## Development

### Code Quality

Format code:
```bash
make black
```

Run all validations (formatting, linting, type checking):
```bash
make validate
```

### Manual Validation

```bash
# Format with Black
uv run black genmeme

# Lint with flake8
uv run flake8 genmeme

# Type check with mypy (strict mode)
uv run mypy genmeme --strict --explicit-package-bases
```

### Code Style Guidelines

- Use strict type checking with mypy
- Follow Black formatting standards
- Keep line length under 120 characters
- Avoid obvious comments - code should be self-explanatory
- Only comment complex logic that isn't immediately clear

## Project Structure

```
memetron3000/
├── genmeme/
│   ├── __init__.py
│   ├── server.py           # FastAPI web server
│   ├── gen.py              # Meme generation logic
│   ├── llm.py              # LLM API integration
│   ├── db.py               # Database models
│   ├── queue.py            # Job queue manager
│   ├── thumbnails.py       # Thumbnail generation
│   ├── files.py            # Path constants
│   └── prompts/
│       └── gen.jinja       # Prompt template
├── static/
│   ├── index.html          # Main UI
│   └── gallery.html        # Gallery UI
├── images/                 # Meme template images
├── output/                 # Generated memes
│   └── thumbnails/         # Generated thumbnails
├── scripts/                # Utility scripts
├── templates.json          # Meme template definitions
├── pyproject.toml          # Project configuration
├── Makefile               # Development tasks
└── download.sh            # Download template images

```

## Technologies Used

- **FastAPI** - Modern web framework for building APIs
- **SQLAlchemy** - Database ORM for metadata storage
- **OpenRouter** - API gateway for accessing LLMs
- **Google Gemini 3 Pro Image** - Vision-capable LLM for meme generation
- **Jinja2** - Template engine for prompt generation
- **Pillow** - Image processing for thumbnails
- **uvicorn** - ASGI server
- **aiohttp** - Async HTTP client
- **Pydantic** - Data validation

## License

This project is provided as-is for educational and research purposes.

## Credits

Created by [IlyaGusev](https://github.com/IlyaGusev)
