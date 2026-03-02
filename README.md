# Kaggle Sherd Data Explorer

A modern, responsive web application to explore and search archaeological sherd data from the `sherds.db` database.

## Features

- **Responsive Design**: Optimized for both desktop (table view) and mobile (card view) devices.
- **Advanced Search**: Filter by Sherd ID, Unit, Part, Type, and Image Side.
- **Dynamic Metadata**: Filters are automatically populated with unique values from the database.
- **Efficient Pagination**: Handles large datasets (35,000+ rows) with server-side pagination.
- **Image Preview**: Click on any thumbnail to view an enlarged version in a high-resolution modal.

## Tech Stack

- **Backend**: Python, FastAPI, SQLite3, Jinja2
- **Frontend**: Vanilla HTML5, CSS3 (with Responsive Design), and JavaScript (ES6+)
- **Environment**: Managed with `uv`

## Getting Started

### Prerequisites

Ensure you have [uv](https://github.com/astral-sh/uv) installed.

### Installation

Install the required dependencies:

```bash
uv add fastapi uvicorn jinja2
```

### Running the Application

Start the FastAPI server:

```bash
uv run python server.py
```

The application will be available at `http://localhost:8000`.

## Project Structure

- `server.py`: FastAPI backend handling API requests and serving static files.
- `templates/index.html`: Main frontend template with responsive UI logic.
- `sherds.db`: SQLite database containing the `sherd_info` table.
- `h690/sherd_images/`: Directory containing the sherd image assets.

## Database Schema

The application uses the `sherd_info` table with the following structure:

- `image_id` (TEXT, PRIMARY KEY)
- `sherd_id` (TEXT)
- `unit` (TEXT)
- `part` (TEXT)
- `type` (TEXT)
- `image_side` (TEXT)
- ... (and other metadata fields)
