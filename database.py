from pymongo import MongoClient
from pydantic import BaseModel, EmailStr
from datetime import datetime

client = MongoClient("mongodb://localhost:27017")
db = client["print_ease"]
users_col = db["users"]
orders_col = db["orders"]

class RegisterUser(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str = "Not Provided"
    address: str = "Not Provided"

class LoginUser(BaseModel):
    email: EmailStr
    password: str