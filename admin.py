from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from database import db
import jwt
import os

router = APIRouter( tags=["Admin"])

security = HTTPBearer()
SECRET_KEY = os.getenv("SECRET_KEY")

# ==========================
# 🔐 VERIFY ADMIN
# ==========================
def verify_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_email = payload.get("email")

        user = db.users.find_one({"email": user_email})

        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        if user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        return user

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ==========================
# 📦 GET ALL ORDERS
# ==========================
@router.get("/orders")
def get_admin_orders(admin=Depends(verify_admin)):
    orders = list(db.orders.find().sort("_id", -1))

    for order in orders:
        order["_id"] = str(order["_id"])

    return orders


# ==========================
# ✅ MARK ORDER COMPLETED
# ==========================
@router.put("/orders/{order_id}/complete")
def complete_order(order_id: str, admin=Depends(verify_admin)):
    result = db.orders.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"status": "completed"}}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Order not found")

    return {"message": "Order marked as completed"}