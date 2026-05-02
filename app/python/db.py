import mysql.connector

DB_CONFIG = {
    "host": "localhost",
    "port": 8889,
    "user": "root",
    "password": "root",
    'unix_socket': '/Applications/MAMP/tmp/mysql/mysql.sock',
    "database": "loan_manager"
}

# %s is a parameterized placeholder. The DB driver substitutes the actual values
# at runtime, keeping query structure and data separate (prevents SQL injection).
def query(sql, params=None, fetch=True):
    conn = mysql.connector.connect(**DB_CONFIG)
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    if fetch:
        result = cur.fetchall()
        cur.close()
        conn.close()
        return result
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    conn.close()
    return last_id
