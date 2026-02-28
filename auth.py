from datetime import datetime, timedelta # timedelta add kiya
import bcrypt
from jose import jwt, JWTError
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import users_col, RegisterUser, LoginUser

router = APIRouter()
security = HTTPBearer()
SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 3 # Token 1 din tak chalega

# Token verify karne ka helper function
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or Expired Token")

@router.post("/register")
def register(user: RegisterUser):
    if users_col.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="User already exists")
    hashed_pw = bcrypt.hashpw(user.password.encode("utf-8"), bcrypt.gensalt())
    users_col.insert_one({
        "name": user.name, "email": user.email, "password": hashed_pw,
        "phone": user.phone, "address": user.address, "created_at": datetime.now()
    })
    return {"message": "User registered successfully"}

@router.post("/login")
def login(user: LoginUser):
    db_user = users_col.find_one({"email": user.email})
    if not db_user or not bcrypt.checkpw(user.password.encode("utf-8"), db_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # Expiry time set karna (24 hours from now)
    access_token_expires = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    # Token mein 'exp' claim add karna zaroori hai
    token_data = {
        "email": user.email,
        "exp": access_token_expires 
    }
    
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token}

# --- YEH NAYA ROUTE HAI FRONTEND REFRESH KE LIYE ---
@router.get("/profile")
def get_profile(payload: dict = Depends(verify_token)):
    email = payload.get("email")
    db_user = users_col.find_one({"email": email}, {"password": 0, "_id": 0}) # Password mat bhejna
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user