# Peblo TV Mini

A lightweight content management system (CMS) and publishing pipeline for episodic video content. Built with a FastAPI backend and a React (Vite + TypeScript) frontend.

## Features

- **Hierarchical Content Structure**: Handles shows, seasons, and multilingual episode groups using SQLAlchemy ORM.
- **Pre-Publish Validation**: Checks for missing metadata (titles, categories) and enforces uniqueness on episode identifiers (`content_group` + `language`).
- **Asset Processing**: Validates uploaded image dimensions (2:3 aspect ratio for posters) and enforces a strict 200KB file size ceiling using Pillow.
- **Atomic State Transitions**: Guarantees all-or-nothing publishing state updates (`DRAFT` to `PUBLISHED`) with audit logs stored in a dedicated `PublishRun` table.
- **Admin vs. Viewer Modes**: Dual-view dashboard allowing operators to edit metadata, resolve content conflicts, and preview published catalog states.

## Tech Stack

- **Backend**: Python 3, FastAPI, SQLAlchemy, SQLite, Pillow, Pydantic
- **Frontend**: React 18, TypeScript, Vite, Axios, Plain CSS

## Project Setup

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy pillow python-multipart

# Start development server
uvicorn app.main:app --reload

# Open a new terminal and navigate to frontend directory
cd cms-ui

# Install dependencies
npm install

# Start Vite dev server
npm run dev



