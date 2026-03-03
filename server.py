import sqlite3
from typing import List, Optional
from fastapi import FastAPI, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
from ultralytics import SAM
from sklearn.decomposition import PCA

app = FastAPI()

# Database helper
DB_PATH = "sherds.db"

# Load the SAM model
MODEL_PATH = "mobile_sam.pt"
sam_model = SAM(MODEL_PATH)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Static files for images
if os.path.exists("h690/sherd_images"):
    app.mount("/images", StaticFiles(directory="h690/sherd_images"), name="images")

templates = Jinja2Templates(directory="templates")

class SegmentRequest(BaseModel):
    image_id: str
    bbox: List[float]  # [x1, y1, x2, y2]

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/segment")
async def segment_image(req: SegmentRequest):
    img_path = os.path.join("h690/sherd_images", f"{req.image_id}.jpg")
    if not os.path.exists(img_path):
        return {"error": "Image not found"}
    
    img = cv2.imread(img_path)
    if img is None:
        return {"error": "Failed to load image"}
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Run SAM
    # SAM expects bboxes as a list of lists: [[x1, y1, x2, y2]]
    results = sam_model(img_rgb, bboxes=[req.bbox], verbose=False)
    
    if not results or results[0].masks is None:
        return {"error": "No mask found"}
    
    # Get the first mask
    mask = results[0].masks.data[0].cpu().numpy()
    
    # Create a transparent overlay
    h, w = mask.shape
    overlay = np.zeros((h, w, 4), dtype=np.uint8)
    
    # Green mask with some transparency
    overlay[mask > 0.5] = [0, 255, 0, 128] 
    
    # Convert to PIL Image
    mask_img = Image.fromarray(overlay, 'RGBA')
    
    # Save to buffer
    buffered = BytesIO()
    mask_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return {"mask": f"data:image/png;base64,{img_str}"}

@app.post("/api/visualize-embeddings")
async def visualize_embeddings(req: SegmentRequest):
    img_path = os.path.join("h690/sherd_images", f"{req.image_id}.jpg")
    if not os.path.exists(img_path):
        return {"error": "Image not found"}
    
    img = cv2.imread(img_path)
    if img is None:
        return {"error": "Failed to load image"}
    
    img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # 1. Run SAM
    sam_model.predictor.set_image(img_rgb)
    results = sam_model(img_rgb, bboxes=[req.bbox], verbose=False)
    
    # 2. Extract features (usually 256 channels)
    if sam_model.predictor.features is None:
        return {"error": "Failed to extract features"}
        
    features = sam_model.predictor.features.squeeze().cpu().detach().numpy() # [256, 64, 64]
    c, h, w = features.shape
    
    # 3. PCA to 3 components for RGB visualization
    features_flat = features.reshape(c, -1).T # [4096, 256]
    pca = PCA(n_components=3)
    pca_features = pca.fit_transform(features_flat)
    
    # 4. Normalize to [0, 255]
    pca_min = pca_features.min(axis=0)
    pca_max = pca_features.max(axis=0)
    pca_norm = (pca_features - pca_min) / (pca_max - pca_min + 1e-8)
    pca_rgb = (pca_norm * 255).astype(np.uint8)
    
    # 5. Reshape and upscale
    pca_img = pca_rgb.reshape(h, w, 3)
    pca_img_resized = cv2.resize(pca_img, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    
    # 6. Optional: Mask the visualization
    if results and results[0].masks is not None:
        mask = results[0].masks.data[0].cpu().numpy()
        # Ensure mask shape matches rendered image dimensions.
        if mask.shape != pca_img_resized.shape[:2]:
            mask = cv2.resize(mask, (pca_img_resized.shape[1], pca_img_resized.shape[0]), interpolation=cv2.INTER_NEAREST)
        # Dim areas outside confident mask region.
        outside_mask = mask <= 0.5
        pca_img_resized[outside_mask] = pca_img_resized[outside_mask] // 4

    # Save to buffer
    viz_img = Image.fromarray(pca_img_resized)
    buffered = BytesIO()
    viz_img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return {"viz": f"data:image/png;base64,{img_str}"}

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
