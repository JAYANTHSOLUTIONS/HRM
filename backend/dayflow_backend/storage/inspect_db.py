import pymysql

conn = pymysql.connect(
    host='localhost', port=3306, user='root', password='4048', database='dayflow_hrms',
    cursorclass=pymysql.cursors.DictCursor
)
cur = conn.cursor()

tables = [
    'users', 'employees', 'departments', 'designations', 'attendance',
    'leave_balances', 'leave_requests', 'salary_structures', 'salary_components', 'holidays'
]

for t in tables:
    cur.execute(f'DESCRIBE {t}')
    cols = [f"{r['Field']} ({r['Type']}, Null={r['Null']}, Key={r['Key']})" for r in cur.fetchall()]
    print(f"\n=== {t} ===")
    for c in cols:
        print("  ", c)

conn.close()
