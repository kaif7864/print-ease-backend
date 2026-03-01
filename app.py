import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles # Static files ke liye
import auth
import orders

from admin import router as admin_router

app = FastAPI(title="PrintEase API")

app.include_router(admin_router, prefix="/admin", tags=["Admin"])

# --- CORS Configuration ---
# Isse frontend (React) aur backend (FastAPI) aapas mein baat kar payenge
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Production mein ise frontend URL se replace karein
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

# --- Uploads Folder Setup ---
# Isse 'uploads' folder ki files URL ke zariye access ki ja sakti hain
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- Routes Inclusion ---
# Auth aur Orders ke routers ko yahan connect kiya gaya hai
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "PrintEase API is running modularly!",
        "docs": "/docs" # FastAPI auto-generated documentation link
    }

# Run command: uvicorn app:app --reload