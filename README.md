# D&D 3.5 Monster Advancer

Web port of a D&D 3.5 monster advancement tool originally built in Excel.
Lets you advance monsters by HD, apply ability score increases, add feats, equip armor, and add NPC/base class levels.

## Stack

- **Backend** — Python 3.x, FastAPI, SQLAlchemy, SQLite
- **Frontend** — Single `frontend/index.html` file, no build step

## Setup

**1. Create the virtual environment**
```
python -m venv venv
venv\Scripts\pip install fastapi "uvicorn[standard]" sqlalchemy pydantic openpyxl
```

**2. Build the database**
Requires `MonsterAdvancer_15.02.xlsm` in the project root.
```
venv\Scripts\python backend/data/extract_excel.py
```

**3. Start the server**
```
start.bat
```
`start.bat` checks all requirements before launching and prints instructions if anything is missing.

## Usage

Open `frontend/index.html` in a browser while the server is running on `http://localhost:8000`.

- Search and filter monsters in the right panel
- Click a monster to load its stat block
- Use **▲/▼** to advance HD — stat changes highlight green/red vs base
- Use **Options** to assign ASI points, add feats, and equip armor

## API

Interactive docs at `http://localhost:8000/docs` when the server is running.
