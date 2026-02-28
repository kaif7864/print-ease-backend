import os
import urllib.parse
from pymongo import MongoClient
from pydantic import BaseModel, EmailStr
from datetime import datetime
from dotenv import load_dotenv # 👈 Ye library install karni hogi: pip install python-dotenv

load_dotenv()

user = os.getenv("MONGO_USER")
password = os.getenv("MONGO_PASSWORD")
cluster_url = os.getenv("MONGO_CLUSTER_URL")

encoded_password = urllib.parse.quote_plus(password)

MONGO_URI = f"mongodb+srv://{user}:{encoded_password}@{cluster_url}/PrintEase?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client["print_ease"]
users_col = db["users"]
orders_col = db["orders"]

# database.py
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000) # 5 seconds timeout

try:
    client.admin.command('ping')
    print("✅ Atlas Connected Successfully!")
except Exception as e:
    print(f"❌ Connection Failed: {e}")

class RegisterUser(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str = "Not Provided"
    address: str = "Not Provided"

class LoginUser(BaseModel):
    email: EmailStr
    password: str