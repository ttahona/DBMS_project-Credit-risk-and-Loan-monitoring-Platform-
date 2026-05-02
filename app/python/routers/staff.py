from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from datetime import date, timedelta
from db import query
from auth import get_current_user
from audit import write_audit_log

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "frontend" / "templates"))
_approved_by_ready = False


class LoanActionBody(BaseModel):
    loan_id: int


from auth import require_role
staff_only = require_role("staff")


def classify_risk(loan_id):
    emis = query("""
        SELECT due_date
        FROM   EMI_Schedule
        WHERE  loan_id = %s
          AND  status != 'Paid'
        ORDER BY due_date
    """, (loan_id,))
    if not emis:
        return 1
    today = date.today()
    max_days = max(
        ((today - e["due_date"]).days for e in emis if e["due_date"] < today),
        default=0
    )
    if max_days == 0:  return 1
    if max_days <= 30: return 2
    if max_days <= 60: return 3
    return 4

def upsert_risk(loan_id):
    bucket_id = classify_risk(loan_id)
    exists = query("SELECT risk_id FROM Loan_Risk_Status WHERE loan_id = %s", (loan_id,))
    if exists:
        query("""
            UPDATE Loan_Risk_Status
            SET    bucket_id = %s, assessed_date = %s
            WHERE  loan_id = %s
        """, (bucket_id, date.today(), loan_id), fetch=False)
    else:
        query("""
            INSERT INTO Loan_Risk_Status (loan_id, bucket_id, assessed_date)
            VALUES (%s, %s, %s)
        """, (loan_id, bucket_id, date.today()), fetch=False)


def ensure_approved_by_column():
    global _approved_by_ready
    if _approved_by_ready:
        return
    exists = query("""
        SELECT COUNT(*) AS c
        FROM   INFORMATION_SCHEMA.COLUMNS
        WHERE  TABLE_SCHEMA = DATABASE()
          AND  TABLE_NAME = 'Loan'
          AND  COLUMN_NAME = 'approved_by'
    """)[0]["c"]
    if not exists:
        query("ALTER TABLE Loan ADD COLUMN approved_by CHAR(16) NULL", fetch=False)
    col_type = query("""
        SELECT DATA_TYPE AS t
        FROM   INFORMATION_SCHEMA.COLUMNS
        WHERE  TABLE_SCHEMA = DATABASE()
          AND  TABLE_NAME = 'Loan'
          AND  COLUMN_NAME = 'approved_by'
        LIMIT 1
    """)[0]["t"]
    if col_type.lower() != "char":
        query("ALTER TABLE Loan MODIFY COLUMN approved_by CHAR(16) NULL", fetch=False)
    fk_exists = query("""
        SELECT COUNT(*) AS c
        FROM   INFORMATION_SCHEMA.KEY_COLUMN_USAGE
        WHERE  TABLE_SCHEMA = DATABASE()
          AND  TABLE_NAME = 'Loan'
          AND  COLUMN_NAME = 'approved_by'
          AND  REFERENCED_TABLE_NAME = 'Staff'
    """)[0]["c"]
    if not fk_exists:
        query("ALTER TABLE Loan ADD CONSTRAINT fk_loan_approved_by FOREIGN KEY (approved_by) REFERENCES Staff(staff_id)", fetch=False)
    _approved_by_ready = True


@router.get("/")
def staff_home(request: Request):
    return templates.TemplateResponse(request, "staff/index.html")


@router.get("/loan-requests")
def loan_requests(user=Depends(staff_only)):
    return query("""
        SELECT l.*, b.name AS borrower_name
        FROM   Loan AS l
        INNER JOIN Borrower AS b ON l.borrower_id = b.borrower_id
        WHERE  l.branch_id = %s
          AND  l.status = 'Pending'
    """, (user["branch_id"],))

@router.post("/loan-requests/approve")
def approve_loan(body: LoanActionBody, user=Depends(staff_only)):
    ensure_approved_by_column()
    loans = query("SELECT * FROM Loan WHERE loan_id = %s AND branch_id = %s", (body.loan_id, user["branch_id"]))
    if not loans:
        raise HTTPException(status_code=404, detail="Loan not found")
    loan = loans[0]
    staff_rows = query("SELECT staff_id FROM Staff WHERE user_id = %s", (user["user_id"],))
    if not staff_rows:
        raise HTTPException(status_code=404, detail="Staff record not found")
    staff_id = staff_rows[0]["staff_id"]
    query("""
        UPDATE Loan
        SET    status = 'Active', start_date = %s, approved_by = %s
        WHERE  loan_id = %s
    """, (date.today(), staff_id, body.loan_id), fetch=False)
    write_audit_log("Loan", body.loan_id, "APPROVE", user=user, note="Loan #{} approved".format(body.loan_id))
    emi_amount = round(loan["amount"] * (1 + loan["interest_rate"] / 100) / loan["tenure_months"], 2)
    for i in range(1, loan["tenure_months"] + 1):
        query("""
            INSERT INTO EMI_Schedule (loan_id, emi_number, due_date, amount_due, status)
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (body.loan_id, i, date.today() + timedelta(days=30 * i), emi_amount), fetch=False)
    upsert_risk(body.loan_id)
    return {"ok": True}

@router.post("/loan-requests/reject")
def reject_loan(body: LoanActionBody, user=Depends(staff_only)):
    query("UPDATE Loan SET status = 'Rejected' WHERE loan_id = %s AND branch_id = %s",
          (body.loan_id, user["branch_id"]), fetch=False)
    write_audit_log("Loan", body.loan_id, "REJECT", user=user, note="Loan #{} rejected".format(body.loan_id))
    return {"ok": True}


@router.get("/branch-users")
def branch_users(user=Depends(staff_only)):
    return query("""
        SELECT 'borrower' AS role, b.borrower_id AS profile_id, u.username, b.name,
               b.email, b.phone
        FROM   Borrower AS b
        LEFT JOIN User AS u ON b.user_id = u.user_id
        WHERE  b.branch_id = %s
    """, (user["branch_id"],))


@router.get("/loan-monitoring")
def loan_monitoring(user=Depends(staff_only)):
    loans = query("""
        SELECT l.loan_id, l.borrower_id, l.amount, l.status, l.start_date,
               b.name AS borrower_name, rb.bucket_name
        FROM   Loan AS l
        INNER JOIN Borrower AS b ON l.borrower_id = b.borrower_id
        LEFT JOIN Loan_Risk_Status AS lrs ON l.loan_id = lrs.loan_id
        LEFT JOIN Risk_Bucket AS rb ON lrs.bucket_id = rb.bucket_id
        WHERE  l.branch_id = %s
          AND  l.status IN ('Active', 'Completed')
        ORDER BY l.loan_id DESC
    """, (user["branch_id"],))

    for loan in loans:
        paid = query("SELECT COUNT(*) AS c FROM EMI_Schedule WHERE loan_id = %s AND status = 'Paid'", (loan["loan_id"],))[0]["c"]
        total = query("SELECT COUNT(*) AS c FROM EMI_Schedule WHERE loan_id = %s", (loan["loan_id"],))[0]["c"]
        next_due = query("""
            SELECT due_date
            FROM   EMI_Schedule
            WHERE  loan_id = %s
              AND  status = 'Pending'
            ORDER BY emi_number
            LIMIT 1
        """, (loan["loan_id"],))
        loan["paid_emis"] = paid
        loan["total_emis"] = total
        loan["next_due_date"] = str(next_due[0]["due_date"]) if next_due else None

    return loans


@router.get("/active-loans")
def active_loans(user=Depends(staff_only)):
    loans = query("""
        SELECT l.loan_id, l.borrower_id, l.amount, l.status, l.start_date, l.loan_type,
               b.name AS borrower_name, rb.bucket_name
        FROM   Loan AS l
        INNER JOIN Borrower AS b ON l.borrower_id = b.borrower_id
        LEFT  JOIN Loan_Risk_Status AS lrs ON l.loan_id = lrs.loan_id
        LEFT  JOIN Risk_Bucket AS rb ON lrs.bucket_id = rb.bucket_id
        WHERE  l.branch_id = %s AND l.status = 'Active'
        ORDER BY l.loan_id DESC
    """, (user["branch_id"],))
    for loan in loans:
        paid  = query("SELECT COUNT(*) AS c FROM EMI_Schedule WHERE loan_id = %s AND status = 'Paid'",
                      (loan["loan_id"],))[0]["c"]
        total = query("SELECT COUNT(*) AS c FROM EMI_Schedule WHERE loan_id = %s",
                      (loan["loan_id"],))[0]["c"]
        next_due = query("""
            SELECT due_date FROM EMI_Schedule
            WHERE  loan_id = %s AND status = 'Pending'
            ORDER  BY emi_number LIMIT 1
        """, (loan["loan_id"],))
        loan["paid_emis"]     = paid
        loan["total_emis"]    = total
        loan["next_due_date"] = str(next_due[0]["due_date"]) if next_due else None
    return loans


@router.get("/loan-archive")
def loan_archive(user=Depends(staff_only)):
    return query("""
        SELECT l.loan_id, l.amount, l.status, l.start_date, l.loan_type,
               b.name AS borrower_name
        FROM   Loan AS l
        INNER JOIN Borrower AS b ON l.borrower_id = b.borrower_id
        WHERE  l.branch_id = %s AND l.status IN ('Completed', 'Rejected')
        ORDER BY l.loan_id DESC
    """, (user["branch_id"],))


@router.get("/audit-logs")
def staff_audit_logs(user=Depends(staff_only)):
    username_rows = query("SELECT username FROM User WHERE user_id = %s", (user["user_id"],))
    username = username_rows[0]["username"] if username_rows else ""
    return query("""
        SELECT change_date, changed_by, table_name, action, new_value AS note
        FROM   Audit_Log
        WHERE  changed_by = %s
           OR  (table_name = 'Loan' AND record_id IN (
                   SELECT loan_id FROM Loan WHERE branch_id = %s))
           OR  (table_name = 'Payment' AND record_id IN (
                   SELECT p.payment_id FROM Payment AS p
                   JOIN   Loan AS l ON p.loan_id = l.loan_id
                   WHERE  l.branch_id = %s))
        ORDER BY log_id DESC
        LIMIT 200
    """, (username, user["branch_id"], user["branch_id"]))
