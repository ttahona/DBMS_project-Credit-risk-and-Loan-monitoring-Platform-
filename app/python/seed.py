"""
Run from the app/ directory:  python seed.py
Inserts two branches, one admin, two staff (one per branch),
and two borrowers (one per branch).
Passwords are all:  password123
"""
from db import query
from auth import hash_password, new_id

PW = "password123"


def insert_user(username, role):
    uid = new_id()
    query(
        "INSERT INTO User (user_id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
        (uid, username, hash_password(PW), role),
        fetch=False
    )
    return uid


# ── Branches ──────────────────────────────────────────────────────────────────
query("INSERT INTO Branch (branch_name, location) VALUES (%s, %s)", ("Downtown Branch", "New York"), fetch=False)
query("INSERT INTO Branch (branch_name, location) VALUES (%s, %s)", ("Uptown Branch",   "Chicago"),  fetch=False)

branches = query("SELECT branch_id, branch_name FROM Branch ORDER BY branch_id")
b1, b2 = branches[0]["branch_id"], branches[1]["branch_id"]
print(f"Branches: {branches[0]['branch_name']} (id={b1}), {branches[1]['branch_name']} (id={b2})")

# ── Admin ─────────────────────────────────────────────────────────────────────
uid = insert_user("admin1", "admin")
aid = new_id()
query("INSERT INTO Admin (admin_id, user_id, name) VALUES (%s, %s, %s)", (aid, uid, "Alice Admin"), fetch=False)
print(f"Admin:    admin1 / {PW}")

# ── Staff ─────────────────────────────────────────────────────────────────────
uid = insert_user("staff_downtown", "staff")
sid = new_id()
query("INSERT INTO Staff (staff_id, user_id, name, branch_id) VALUES (%s, %s, %s, %s)", (sid, uid, "Bob Staff", b1), fetch=False)
print(f"Staff:    staff_downtown / {PW}  (branch: Downtown)")

uid = insert_user("staff_uptown", "staff")
sid = new_id()
query("INSERT INTO Staff (staff_id, user_id, name, branch_id) VALUES (%s, %s, %s, %s)", (sid, uid, "Carol Staff", b2), fetch=False)
print(f"Staff:    staff_uptown / {PW}  (branch: Uptown)")

# ── Borrowers ─────────────────────────────────────────────────────────────────
uid = insert_user("borrower1", "borrower")
query(
    "INSERT INTO Borrower (user_id, name, phone, address, email, dob, pan_no, branch_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
    (uid, "David Borrower", "555-0101", "123 Main St, New York", "david@example.com", "1990-05-15", "ABCDE1234F", b1),
    fetch=False
)
print(f"Borrower: borrower1 / {PW}  (branch: Downtown)")

uid = insert_user("borrower2", "borrower")
query(
    "INSERT INTO Borrower (user_id, name, phone, address, email, dob, pan_no, branch_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
    (uid, "Eva Borrower", "555-0202", "456 Oak Ave, Chicago", "eva@example.com", "1985-11-30", "FGHIJ5678K", b2),
    fetch=False
)
print(f"Borrower: borrower2 / {PW}  (branch: Uptown)")

# ── Risk Bucket seed (safe to re-run, will error if already exists — ignore) ──
for row in [(1,"Current"),(2,"30+ Days"),(3,"60+ Days"),(4,"90+ Days")]:
    try:
        query("INSERT INTO Risk_Bucket (bucket_id, bucket_name) VALUES (%s, %s)", row, fetch=False)
    except Exception:
        pass

print("\nDone. All users created with password:", PW)
