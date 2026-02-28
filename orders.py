import os
import shutil
import json
from typing import List
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from database import orders_col
from auth import verify_token

router = APIRouter()
UPLOAD_DIR = "uploads"

if not os.path.exists(UPLOAD_DIR): 
    os.makedirs(UPLOAD_DIR)

@router.post("/create-order")
async def create_order(
    files: List[UploadFile] = File(...), 
    metadata: List[str] = Form(...), 
    payment_id: str = Form(...),
    total_amount: float = Form(...),
    payload: dict = Depends(verify_token)
):
    try:
        saved_items = []
        for i, upload in enumerate(files):
            file_extension = os.path.splitext(upload.filename)[1]
            file_name = f"{datetime.now().timestamp()}_{i}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, file_name)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)
            
            # JSON string ko dictionary mein badlein
            item_settings = json.loads(metadata[i])
            
            saved_items.append({
                "fileName": item_settings.get('fileName', upload.filename),
                "file_path": file_path,
                "type": item_settings.get('type', 'bw'),
                "copies": int(item_settings.get('copies', 1)),
                "binding": bool(item_settings.get('binding', False)),
                "price": float(item_settings.get('price', 0))
            })

        order_data = {
            "user_email": payload["email"],
            "payment_id": payment_id,
            "items": saved_items,
            "total_price": total_amount,
            "order_status": "Processing",
            "created_at": datetime.now()
        }
        
        result = orders_col.insert_one(order_data)
        return {"status": "success", "order_id": str(result.inserted_id)}

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-orders")
async def get_my_orders(payload: dict = Depends(verify_token)):
    orders = list(orders_col.find({"user_email": payload["email"]}).sort("created_at", -1))
    for order in orders:
        order["_id"] = str(order["_id"])
        if isinstance(order["created_at"], datetime):
            order["created_at"] = order["created_at"].isoformat()
    return orders