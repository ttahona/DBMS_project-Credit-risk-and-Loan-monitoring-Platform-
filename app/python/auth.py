import bcrypt
from uuid import uuid4
from fastapi import HTTPException, Header, Depends

sessions = {}

def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()

def verify_password(plain, hashed):
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def new_id():
    return str(uuid4().int)[:16]

def create_session(user_id, role, branch_id=None):
    token = uuid4().hex
    sessions[token] = {"user_id": user_id, "role": role, "branch_id": branch_id}
    return token

def get_current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization[7:]
    user = sessions.get(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired")
    return user

def require_role(role: str):
    def role_check(user=Depends(get_current_user)):
        if user["role"] != role:
            raise HTTPException(status_code=403, detail=f"{role.title()} only")
        return user
    return role_check
