import os
import json
import hmac
import hashlib
import razorpay
import cloudinary
import cloudinary.uploader
from typing import List
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Request
from database import orders_col
from auth import verify_token

router = APIRouter(tags=["Orders"])

# =========================================
# ☁️ CLOUDINARY CONFIGURATION
# =========================================
cloudinary.config( 
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"), 
    api_key = os.getenv("CLOUDINARY_API_KEY"), 
    api_secret = os.getenv("CLOUDINARY_API_SECRET"),
    secure = True
)

# Razorpay Client
razorpay_client = razorpay.Client(auth=(
    os.getenv("RAZORPAY_KEY_ID"),
    os.getenv("RAZORPAY_KEY_SECRET")
))

# =========================================
# 1️⃣ CREATE RAZORPAY ORDER
# =========================================
@router.post("/create-razorpay-order")
async def create_razorpay_order(data: dict):
    try:
        amount = data.get("amount")
        if not amount:
            raise HTTPException(status_code=400, detail="Amount required")

        clean_amount = int(float(amount) * 100)
        order = razorpay_client.order.create({
            "amount": clean_amount,
            "currency": "INR",
            "payment_capture": 1
        })
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# 2️⃣ VERIFY PAYMENT
# =========================================
@router.post("/verify-payment")
async def verify_payment(request: Request):
    try:
        body = await request.json()
        payment_id = body.get("razorpay_payment_id")
        order_id = body.get("razorpay_order_id")
        signature = body.get("razorpay_signature")

        if not payment_id or not order_id or not signature:
            raise HTTPException(status_code=400, detail="Invalid payment data")

        secret = os.getenv("RAZORPAY_KEY_SECRET")
        generated_signature = hmac.new(
            secret.encode(),
            f"{order_id}|{payment_id}".encode(),
            hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(generated_signature, signature):
            return {"status": "verified"}
        else:
            return {"status": "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================
# 3️⃣ SAVE FINAL ORDER (WITH CLOUDINARY PRESET & TAGS)
# =========================================
@router.post("/create-order")
async def create_order(
    files: List[UploadFile] = File(...),
    metadata: List[str] = Form(...),
    payment_id: str = Form(...),
    total_amount: float = Form(...),
    payload: dict = Depends(verify_token)
):
    try:
        # Prevent duplicate order
        existing_order = orders_col.find_one({"payment_id": payment_id})
        if existing_order:
            raise HTTPException(status_code=400, detail="Order already exists")

        saved_items = []

        for i, upload in enumerate(files):
            item_settings = json.loads(metadata[i])
            # --- UPDATED CLOUDINARY UPLOAD LOGIC ---
            upload_result = cloudinary.uploader.upload(
                upload.file, 
                upload_preset = "print-ease-preset", # Jo aapne dashboard mein banaya hai
                resource_type = "auto",
                # Tags jo 7-day cleanup mein help karenge
                tags = ["temporary_file", f"uploaded_on_{datetime.now().strftime('%Y-%m-%d')}"]
            )
            
            file_url = upload_result.get("secure_url")

            saved_items.append({
                "fileName": item_settings.get('fileName', upload.filename),
                "file_path": file_url,
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
            "order_status": "Paid",
            "created_at": datetime.now()
        }

        result = orders_col.insert_one(order_data)
        return {"status": "success", "order_id": str(result.inserted_id)}

    except Exception as e:
        print(f"Cloudinary Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Order creation or File upload failed")

# =========================================
# 4️⃣ RAZORPAY WEBHOOK & MY ORDERS
# =========================================
@router.post("/razorpay-webhook")
async def razorpay_webhook(request: Request):
    try:
        body = await request.body()
        received_signature = request.headers.get("x-razorpay-signature")
        webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET")

        generated_signature = hmac.new(
            webhook_secret.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(generated_signature, received_signature):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")

        payload = json.loads(body)
        event = payload.get("event")
        payment_id = payload["payload"]["payment"]["entity"]["id"]

        if event == "payment.captured":
            orders_col.update_one({"payment_id": payment_id}, {"$set": {"order_status": "Paid"}})
        elif event == "payment.failed":
            orders_col.update_one({"payment_id": payment_id}, {"$set": {"order_status": "Failed"}})

        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/my-orders")
async def get_my_orders(payload: dict = Depends(verify_token)):
    orders = list(orders_col.find({"user_email": payload["email"]}).sort("created_at", -1))
    for order in orders:
        order["_id"] = str(order["_id"])
    return orders