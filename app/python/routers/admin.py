from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from db import query
from auth import get_current_user, hash_password, new_id
from audit import write_audit_log

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "frontend" / "templates"))


def delete_entity_with_user(table, id_col, id_val, user):
    """Helper: delete entity and its user account, with audit logging"""
    old = query(f"SELECT * FROM {table} WHERE {id_col} = %s", (id_val,))
    if old:
        query(f"DELETE FROM {table} WHERE {id_col} = %s", (id_val,), fetch=False)
        query("DELETE FROM User WHERE user_id = %s", (old[0]["user_id"],), fetch=False)
        write_audit_log(table, id_val, "DELETE", user=user, note="{} deleted".format(table))
    return {"ok": True}


class BranchBody(BaseModel):
    branch_name: str
    location: str

class BorrowerBody(BaseModel):
    username: str
    password: str
    name: str
    phone: str
    address: str
    email: str
    dob: str
    pan_no: str
    branch_id: int

class StaffBody(BaseModel):
    username: str
    password: str
    name: str
    branch_id: int

class AdminBody(BaseModel):
    username: str
    password: str
    name: str


from auth import require_role
admin_only = require_role("admin")


@router.get("/")
def admin_home(request: Request):
    return templates.TemplateResponse(request, "admin/index.html")


@router.get("/branches")
def list_branches(user=Depends(admin_only)):
    return query("SELECT * FROM Branch")

@router.post("/branches")
def create_branch(body: BranchBody, user=Depends(admin_only)):
    branch_id = query("INSERT INTO Branch (branch_name, location) VALUES (%s, %s)", (body.branch_name, body.location), fetch=False)
    write_audit_log("Branch", branch_id, "INSERT", user=user, note="Branch '{}' added".format(body.branch_name))
    return {"ok": True}

@router.delete("/branches/{branch_id}")
def delete_branch(branch_id: int, user=Depends(admin_only)):
    old = query("SELECT * FROM Branch WHERE branch_id = %s", (branch_id,))
    if old:
        query("DELETE FROM Branch WHERE branch_id = %s", (branch_id,), fetch=False)
        write_audit_log("Branch", branch_id, "DELETE", user=user, note="Branch '{}' deleted".format(old[0].get("branch_name", "")))
    return {"ok": True}


@router.get("/borrowers")
def list_borrowers(user=Depends(admin_only)):
    return query("""
        SELECT b.*, u.username, br.branch_name
        FROM   Borrower AS b
        LEFT JOIN User   AS u  ON b.user_id   = u.user_id
        LEFT JOIN Branch AS br ON b.branch_id = br.branch_id
    """)

@router.post("/borrowers")
def create_borrower(body: BorrowerBody, user=Depends(admin_only)):
    uid = new_id()
    hashed = hash_password(body.password)
    query("INSERT INTO User (user_id, username, password_hash, role) VALUES (%s, %s, %s, 'borrower')",
          (uid, body.username, hashed), fetch=False)
    borrower_id = query(
        "INSERT INTO Borrower (user_id, name, phone, address, email, dob, pan_no, branch_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (uid, body.name, body.phone, body.address, body.email, body.dob, body.pan_no, body.branch_id),
        fetch=False)
    write_audit_log("Borrower", borrower_id, "INSERT", user=user, note="Borrower '{}' added".format(body.username))
    return {"ok": True}

@router.delete("/borrowers/{borrower_id}")
def delete_borrower(borrower_id: int, user=Depends(admin_only)):
    return delete_entity_with_user("Borrower", "borrower_id", borrower_id, user)


@router.get("/staff")
def list_staff(user=Depends(admin_only)):
    return query("""
        SELECT s.*, u.username, b.branch_name
        FROM   Staff AS s
        INNER JOIN User   AS u ON s.user_id   = u.user_id
        LEFT  JOIN Branch AS b ON s.branch_id = b.branch_id
    """)

@router.post("/staff")
def create_staff(body: StaffBody, user=Depends(admin_only)):
    uid, sid = new_id(), new_id()
    hashed = hash_password(body.password)
    query("INSERT INTO User (user_id, username, password_hash, role) VALUES (%s, %s, %s, 'staff')",
          (uid, body.username, hashed), fetch=False)
    query("INSERT INTO Staff (staff_id, user_id, name, branch_id) VALUES (%s, %s, %s, %s)",
          (sid, uid, body.name, body.branch_id), fetch=False)
    write_audit_log("Staff", sid, "INSERT", user=user, note="Staff '{}' added".format(body.username))
    return {"ok": True}

@router.delete("/staff/{staff_id}")
def delete_staff(staff_id: str, user=Depends(admin_only)):
    return delete_entity_with_user("Staff", "staff_id", staff_id, user)


@router.get("/admins")
def list_admins(user=Depends(admin_only)):
    return query("""
        SELECT a.*, u.username
        FROM   Admin AS a
        INNER JOIN User AS u ON a.user_id = u.user_id
    """)

@router.post("/admins")
def create_admin(body: AdminBody, user=Depends(admin_only)):
    uid, aid = new_id(), new_id()
    hashed = hash_password(body.password)
    query("INSERT INTO User (user_id, username, password_hash, role) VALUES (%s, %s, %s, 'admin')",
          (uid, body.username, hashed), fetch=False)
    query("INSERT INTO Admin (admin_id, user_id, name) VALUES (%s, %s, %s)",
          (aid, uid, body.name), fetch=False)
    write_audit_log("Admin", aid, "INSERT", user=user, note="Admin '{}' added".format(body.username))
    return {"ok": True}

@router.delete("/admins/{admin_id}")
def delete_admin(admin_id: str, user=Depends(admin_only)):
    return delete_entity_with_user("Admin", "admin_id", admin_id, user)


# ── Update (PUT) endpoints ────────────────────────────────────────────────

class BranchUpdateBody(BaseModel):
    branch_name: str
    location: str

class BorrowerUpdateBody(BaseModel):
    name: str
    phone: str
    address: str
    email: str
    dob: str
    pan_no: str
    branch_id: int

class StaffUpdateBody(BaseModel):
    name: str
    branch_id: int

class AdminUpdateBody(BaseModel):
    name: str


@router.put("/branches/{branch_id}")
def update_branch(branch_id: int, body: BranchUpdateBody, user=Depends(admin_only)):
    old = query("SELECT * FROM Branch WHERE branch_id = %s", (branch_id,))
    if not old:
        raise HTTPException(status_code=404, detail="Branch not found")
    query("UPDATE Branch SET branch_name = %s, location = %s WHERE branch_id = %s",
          (body.branch_name, body.location, branch_id), fetch=False)
    write_audit_log("Branch", branch_id, "UPDATE", user=user, note="Branch '{}' updated".format(body.branch_name))
    return {"ok": True}

@router.put("/borrowers/{borrower_id}")
def update_borrower(borrower_id: int, body: BorrowerUpdateBody, user=Depends(admin_only)):
    old = query("SELECT * FROM Borrower WHERE borrower_id = %s", (borrower_id,))
    if not old:
        raise HTTPException(status_code=404, detail="Borrower not found")
    query("""
        UPDATE Borrower
        SET    name = %s, phone = %s, address = %s, email = %s,
               dob = %s, pan_no = %s, branch_id = %s
        WHERE  borrower_id = %s
    """, (body.name, body.phone, body.address, body.email,
           body.dob, body.pan_no, body.branch_id, borrower_id), fetch=False)
    write_audit_log("Borrower", borrower_id, "UPDATE", user=user, note="Borrower '{}' updated".format(body.name))
    return {"ok": True}

@router.put("/staff/{staff_id}")
def update_staff(staff_id: str, body: StaffUpdateBody, user=Depends(admin_only)):
    old = query("SELECT * FROM Staff WHERE staff_id = %s", (staff_id,))
    if not old:
        raise HTTPException(status_code=404, detail="Staff not found")
    query("UPDATE Staff SET name = %s, branch_id = %s WHERE staff_id = %s",
          (body.name, body.branch_id, staff_id), fetch=False)
    write_audit_log("Staff", staff_id, "UPDATE", user=user, note="Staff '{}' updated".format(body.name))
    return {"ok": True}

@router.put("/admins/{admin_id}")
def update_admin(admin_id: str, body: AdminUpdateBody, user=Depends(admin_only)):
    old = query("SELECT * FROM Admin WHERE admin_id = %s", (admin_id,))
    if not old:
        raise HTTPException(status_code=404, detail="Admin not found")
    query("UPDATE Admin SET name = %s WHERE admin_id = %s",
          (body.name, admin_id), fetch=False)
    write_audit_log("Admin", admin_id, "UPDATE", user=user, note="Admin '{}' updated".format(body.name))
    return {"ok": True}


@router.get("/audit-logs")
def audit_logs(user=Depends(admin_only)):
    return query("""
        SELECT change_date, changed_by, table_name, action, new_value AS note
        FROM   Audit_Log
        ORDER BY log_id DESC
        LIMIT 200
    """)
