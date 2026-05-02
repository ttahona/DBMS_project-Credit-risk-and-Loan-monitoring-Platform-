from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from db import query
from auth import verify_password, create_session, get_current_user, sessions
from routers import admin, staff, borrower

BASE = Path(__file__).parent
FRONTEND = BASE.parent / "frontend"

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(FRONTEND / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND / "templates"))

app.include_router(admin.router, prefix="/admin")
app.include_router(staff.router, prefix="/staff")
app.include_router(borrower.router, prefix="/borrower")

class LoginBody(BaseModel):
    username: str
    password: str
    role: str

@app.get("/")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")

@app.post("/auth/login")
def login(body: LoginBody):
    rows = query("SELECT * FROM User WHERE username = %s AND role = %s", (body.username, body.role))
    if not rows or not verify_password(body.password, rows[0]["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = rows[0]
    branch_id = None
    if body.role == "staff":
        s = query("SELECT branch_id FROM Staff WHERE user_id = %s", (user["user_id"],))
        if s:
            branch_id = s[0]["branch_id"]
    token = create_session(user["user_id"], user["role"], branch_id)
    return {"token": token, "role": user["role"]}

@app.post("/auth/logout")
def logout(user=Depends(get_current_user)):
    for k, v in list(sessions.items()):
        if v["user_id"] == user["user_id"]:
            del sessions[k]
    return {"ok": True}
