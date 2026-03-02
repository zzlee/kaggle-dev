import sqlite3
from typing import List, Optional
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os

app = FastAPI()

# Database helper
DB_PATH = "sherds.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Static files for images
if os.path.exists("h690/sherd_images"):
    app.mount("/images", StaticFiles(directory="h690/sherd_images"), name="images")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/sherds")
async def get_sherds(
    page: int = 1,
    page_size: int = 20,
    sherd_id: Optional[str] = None,
    unit: Optional[str] = None,
    part: Optional[str] = None,
    type: Optional[str] = None,
    image_side: Optional[str] = None,
    search: Optional[str] = None
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            s.image_id, s.sherd_id, s.image_side, s.image_id_original,
            u.name as unit, p.name as part, t.name as type
        FROM sherd_info s
        LEFT JOIN units u ON s.unit_id = u.unit_id
        LEFT JOIN parts p ON s.part_id = p.part_id
        LEFT JOIN types t ON s.type_id = t.type_id
        WHERE 1=1
    """
    params = []
    
    if search:
        query += " AND (s.sherd_id LIKE ? OR s.image_id LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    
    if sherd_id:
        query += " AND s.sherd_id LIKE ?"
        params.append(f"%{sherd_id}%")
    if unit:
        query += " AND u.name = ?"
        params.append(unit)
    if part:
        query += " AND p.name = ?"
        params.append(part)
    if type:
        query += " AND t.name = ?"
        params.append(type)
    if image_side:
        query += " AND s.image_side = ?"
        params.append(image_side)
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM ({query})"
    cursor.execute(count_query, params)
    total_count = cursor.fetchone()[0]
    
    # Get paginated data
    query += " LIMIT ? OFFSET ?"
    params.extend([page_size, (page - 1) * page_size])
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    
    results = [dict(row) for row in rows]
    conn.close()
    
    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
        "data": results
    }

@app.get("/api/metadata")
async def get_metadata():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    metadata = {}
    
    cursor.execute("SELECT name FROM units WHERE name IS NOT NULL ORDER BY name")
    metadata['unit'] = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT name FROM parts WHERE name IS NOT NULL ORDER BY name")
    metadata['part'] = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT name FROM types WHERE name IS NOT NULL ORDER BY name")
    metadata['type'] = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT DISTINCT image_side FROM sherd_info WHERE image_side IS NOT NULL ORDER BY image_side")
    metadata['image_side'] = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return metadata

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
