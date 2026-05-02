from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel
from datetime import date
from typing import Optional
from db import query
from auth import get_current_user
from routers.staff import upsert_risk
from audit import write_audit_log

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent.parent / "frontend" / "templates"))
_approved_by_exists = None


class LoanRequestBody(BaseModel):
    amount: float
    loan_type: str
    tenure_months: int

class PaymentBody(BaseModel):
    loan_id: int
    plan: str
    payment_mode: str
    custom_amount: Optional[float] = None


from auth import require_role
borrower_only = require_role("borrower")

def get_borrower_id(user_id):
    rows = query("SELECT borrower_id FROM Borrower WHERE user_id = %s", (user_id,))
    return rows[0]["borrower_id"] if rows else None


def has_successful_tenure(borrower_id):
    rows = query("SELECT 1 FROM Loan WHERE borrower_id = %s AND status = 'Completed' LIMIT 1", (borrower_id,))
    return bool(rows)


def calculate_interest_rate(loan_type, amount, tenure_months, successful_tenure):
    base_rates = {
        "Personal": 12.0,
        "Home": 8.5,
        "Auto": 9.5,
        "Business": 13.0,
    }

    rate = base_rates.get(loan_type, 12.0)

    if tenure_months > 36:
        rate += 1.0

    if amount > 500000:
        rate += 0.5

    if successful_tenure:
        rate -= 0.1

    return round(rate, 2)


def calculate_repayment_summary(amount, interest_rate, tenure_months):
    total_payment = round(amount * (1 + interest_rate / 100), 2)
    monthly_installment = round(total_payment / tenure_months, 2)
    return monthly_installment, total_payment


def has_approved_by_column():
    global _approved_by_exists
    if _approved_by_exists is not None:
        return _approved_by_exists
    rows = query("""
        SELECT COUNT(*) AS c FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'Loan' AND COLUMN_NAME = 'approved_by'
    """)
    _approved_by_exists = bool(rows[0]["c"])
    return _approved_by_exists


def get_loan_progress_summary(loan_id):
    emis = query("""
        SELECT due_date, amount_due, status
        FROM EMI_Schedule WHERE loan_id = %s ORDER BY emi_number
    """, (loan_id,))
    paid = sum(1 for e in emis if e["status"] == "Paid")
    total = len(emis)
    pending = [e for e in emis if e["status"] == "Pending"]
    remaining_amount = round(sum(e["amount_due"] for e in pending), 2)
    progress_percent = round((paid / total) * 100, 1) if total else 0.0
    next_due = pending[0]["due_date"] if pending else None
    end_due = emis[-1]["due_date"] if emis else None
    return {
        "paid_emis": paid, "total_emis": total, "remaining_emis": max(total - paid, 0),
        "remaining_amount": remaining_amount, "next_due_date": str(next_due) if next_due else None,
        "expected_end_date": str(end_due) if end_due else None, "progress_percent": progress_percent
    }


def get_approved_by_name(loan_id):
    if not has_approved_by_column():
        return None
    rows = query("""
        SELECT u.username AS approved_by_name
        FROM   Loan AS l
        LEFT JOIN Staff AS s ON l.approved_by = s.staff_id
        LEFT JOIN User  AS u ON s.user_id     = u.user_id
        WHERE  l.loan_id = %s
    """, (loan_id,))
    return rows[0]["approved_by_name"] if rows and rows[0]["approved_by_name"] else None


def get_pending_emis(loan_id):
    return query("""
        SELECT emi_id, emi_number, due_date, amount_due
        FROM   EMI_Schedule
        WHERE  loan_id = %s
          AND  status = 'Pending'
        ORDER BY emi_number
    """, (loan_id,))


def get_payment_option_details(borrower_id):
    loans = query("""
        SELECT loan_id, start_date
        FROM   Loan
        WHERE  borrower_id = %s
          AND  status = 'Active'
    """, (borrower_id,))
    result = []
    for loan in loans:
        loan_id = loan["loan_id"]
        pending = get_pending_emis(loan_id)
        if not pending:
            continue
        summary = get_loan_progress_summary(loan_id)
        one_month_amount = round(pending[0]["amount_due"], 2)
        three_month_amount = round(sum(e["amount_due"] for e in pending[:3]), 2)
        result.append({
            "loan_id": loan_id,
            "start_date": str(loan["start_date"]) if loan["start_date"] else None,
            "approved_by": get_approved_by_name(loan_id),
            "paid_emis": summary["paid_emis"],
            "total_emis": summary["total_emis"],
            "remaining_emis": summary["remaining_emis"],
            "remaining_amount": summary["remaining_amount"],
            "next_due_date": summary["next_due_date"],
            "expected_end_date": summary["expected_end_date"],
            "progress_percent": summary["progress_percent"],
            "one_month_amount": one_month_amount,
            "three_month_amount": three_month_amount,
            "full_amount": summary["remaining_amount"],
            "pending_emis": [
                {"emi_number": e["emi_number"], "due_date": str(e["due_date"]), "amount_due": float(e["amount_due"])}
                for e in pending
            ]
        })
    return result


@router.get("/")
def borrower_home(request: Request):
    return templates.TemplateResponse(request, "borrower/index.html")


@router.get("/loans")
def my_loans(user=Depends(borrower_only)):
    bid = get_borrower_id(user["user_id"])
    loans = query("""
        SELECT l.*, br.branch_name
        FROM   Loan AS l
        INNER JOIN Branch AS br ON l.branch_id = br.branch_id
        WHERE  l.borrower_id = %s
    """, (bid,))
    for loan in loans:
        summary = get_loan_progress_summary(loan["loan_id"])
        loan["paid_emis"] = summary["paid_emis"]
        loan["total_emis"] = summary["total_emis"]
        loan["remaining_amount"] = summary["remaining_amount"]
        loan["progress_percent"] = summary["progress_percent"]
        loan["approved_by"] = get_approved_by_name(loan["loan_id"])
    return loans


@router.get("/loans/{loan_id}/details")
def loan_details(loan_id: int, user=Depends(borrower_only)):
    bid = get_borrower_id(user["user_id"])
    rows = query("""
        SELECT l.loan_id, l.amount, l.interest_rate, l.start_date, l.loan_type, l.tenure_months, l.status,
               br.branch_name
        FROM   Loan AS l
        INNER JOIN Branch AS br ON l.branch_id = br.branch_id
        WHERE  l.loan_id = %s
          AND  l.borrower_id = %s
    """, (loan_id, bid))
    if not rows:
        raise HTTPException(status_code=404, detail="Loan not found")
    loan = rows[0]
    summary = get_loan_progress_summary(loan_id)
    monthly_installment, total_payment = calculate_repayment_summary(
        loan["amount"], loan["interest_rate"], loan["tenure_months"]
    )
    loan["approved_by"] = get_approved_by_name(loan_id)
    loan["monthly_installment"] = monthly_installment
    loan["total_payment"] = total_payment
    loan.update(summary)
    return loan

@router.post("/loans/calculate")
def calculate_loan_interest(body: LoanRequestBody, user=Depends(borrower_only)):
    bid = get_borrower_id(user["user_id"])
    if not bid:
        raise HTTPException(status_code=404, detail="Borrower not found")
    successful_tenure = has_successful_tenure(bid)
    interest_rate = calculate_interest_rate(
        body.loan_type,
        body.amount,
        body.tenure_months,
        successful_tenure
    )
    monthly_installment, total_payment = calculate_repayment_summary(body.amount, interest_rate, body.tenure_months)
    return {
        "interest_rate": interest_rate,
        "successful_tenure_discount": successful_tenure,
        "monthly_installment": monthly_installment,
        "total_payment": total_payment
    }

@router.post("/loans/request")
def request_loan(body: LoanRequestBody, user=Depends(borrower_only)):
    rows = query("SELECT borrower_id, branch_id FROM Borrower WHERE user_id = %s", (user["user_id"],))
    if not rows:
        raise HTTPException(status_code=404, detail="Borrower not found")
    bid = rows[0]["borrower_id"]
    branch_id = rows[0]["branch_id"]
    interest_rate = calculate_interest_rate(
        body.loan_type,
        body.amount,
        body.tenure_months,
        has_successful_tenure(bid)
    )
    monthly_installment, total_payment = calculate_repayment_summary(body.amount, interest_rate, body.tenure_months)
    loan_id = query("""
        INSERT INTO Loan (borrower_id, branch_id, amount, interest_rate, loan_type, tenure_months, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
    """, (bid, branch_id, body.amount, interest_rate, body.loan_type, body.tenure_months), fetch=False)
    write_audit_log("Loan", loan_id, "REQUEST", user=user, note="Loan requested: {} for {} months".format(body.loan_type, body.tenure_months))
    return {
        "ok": True,
        "interest_rate": interest_rate,
        "monthly_installment": monthly_installment,
        "total_payment": total_payment
    }


@router.get("/payment-options")
def payment_options(user=Depends(borrower_only)):
    bid = get_borrower_id(user["user_id"])
    return get_payment_option_details(bid)

@router.post("/payments")
def make_payment(body: PaymentBody, user=Depends(borrower_only)):
    bid = get_borrower_id(user["user_id"])
    if not query("SELECT loan_id FROM Loan WHERE loan_id = %s AND borrower_id = %s", (body.loan_id, bid)):
        raise HTTPException(status_code=403, detail="Not your loan")

    pending = get_pending_emis(body.loan_id)
    if not pending:
        raise HTTPException(status_code=400, detail="No pending EMI for this loan")

    plan = body.plan.lower().strip()
    selected_emis = []

    if plan == "one":
        selected_emis = pending[:1]
    elif plan == "three":
        selected_emis = pending[:3]
    elif plan == "full":
        selected_emis = pending
    elif plan == "custom":
        if body.custom_amount is None or body.custom_amount <= 0:
            raise HTTPException(status_code=400, detail="custom_amount must be greater than 0 for custom plan")
        running = 0.0
        target = round(body.custom_amount, 2)
        for emi in pending:
            next_running = round(running + emi["amount_due"], 2)
            if next_running <= target + 0.01:
                selected_emis.append(emi)
                running = next_running
                if abs(running - target) <= 0.01:
                    break
            else:
                break
        if not selected_emis or abs(round(sum(e["amount_due"] for e in selected_emis), 2) - target) > 0.01:
            raise HTTPException(status_code=400, detail="Custom amount must match an exact sum of earliest pending EMIs")
    else:
        raise HTTPException(status_code=400, detail="Invalid payment plan")

    amount_paid = round(sum(e["amount_due"] for e in selected_emis), 2)
    paid_until_emi = selected_emis[-1]["emi_number"]
    payment_id = query("""
        INSERT INTO Payment (loan_id, payment_date, amount_paid, payment_mode)
        VALUES (%s, %s, %s, %s)
    """, (body.loan_id, date.today(), amount_paid, body.payment_mode), fetch=False)
    write_audit_log("Payment", payment_id, "INSERT", user=user, note="Payment {} via {} on Loan #{}".format(amount_paid, body.payment_mode, body.loan_id))

    for emi in selected_emis:
        query("INSERT INTO Payment_Allocation (payment_id, emi_id, allocated_amount) VALUES (%s, %s, %s)",
              (payment_id, emi["emi_id"], emi["amount_due"]), fetch=False)
        query("UPDATE EMI_Schedule SET status = 'Paid' WHERE emi_id = %s", (emi["emi_id"],), fetch=False)

    remaining = query("SELECT 1 FROM EMI_Schedule WHERE loan_id = %s AND status != 'Paid' LIMIT 1", (body.loan_id,))
    if not remaining:
        query("UPDATE Loan SET status = 'Completed' WHERE loan_id = %s", (body.loan_id,), fetch=False)
        write_audit_log("Loan", body.loan_id, "UPDATE", user=user, note="Loan #{} completed".format(body.loan_id))
    upsert_risk(body.loan_id)

    details = query("SELECT start_date FROM Loan WHERE loan_id = %s", (body.loan_id,))[0]
    summary = get_loan_progress_summary(body.loan_id)
    return {
        "ok": True,
        "amount_paid": amount_paid,
        "count_paid": len(selected_emis),
        "receipt": {
            "payment_id": payment_id,
            "payment_date": str(date.today()),
            "loan_id": body.loan_id,
            "plan": plan,
            "payment_mode": body.payment_mode,
            "paid_until_emi": paid_until_emi,
            "loan_start_date": str(details["start_date"]) if details["start_date"] else None,
            "pay_before_date": summary["next_due_date"],
            "expected_end_date": summary["expected_end_date"],
            "paid_emis": summary["paid_emis"],
            "total_emis": summary["total_emis"],
            "remaining_amount": summary["remaining_amount"],
            "progress_percent": summary["progress_percent"]
        }
    }

@router.get("/payments")
def payment_history(user=Depends(borrower_only)):
    bid = get_borrower_id(user["user_id"])
    return query("""
        SELECT p.payment_id, p.loan_id, p.payment_date, p.amount_paid, p.payment_mode
        FROM   Payment AS p
        INNER JOIN Loan AS l ON p.loan_id = l.loan_id
        WHERE  l.borrower_id = %s
        ORDER BY p.payment_date DESC
    """, (bid,))
