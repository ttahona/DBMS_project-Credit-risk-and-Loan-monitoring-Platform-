from datetime import date
from db import query


def _username(user):
    if not user:
        return "system"
    rows = query("SELECT username FROM User WHERE user_id = %s", (user.get("user_id"),))
    return rows[0]["username"] if rows else "unknown"


def write_audit_log(table_name, record_id, action, user=None, note=""):
    query(
        "INSERT INTO Audit_Log (table_name, record_id, action, changed_by, change_date, new_value) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (table_name, record_id, action, _username(user), date.today(), note),
        fetch=False,
    )
