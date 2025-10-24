import sqlite3

conn = sqlite3.connect("data.sqlite")
cursor = conn.cursor()

# Xóa toàn bộ dữ liệu trong hai bảng

# cursor.execute("DELETE FROM ONDUTY")
# cursor.execute("DELETE FROM OFFDUTY")
cursor.execute("DELETE FROM TEACHLOG")


conn.commit()
conn.close()

print("✅ Đã xoá toàn bộ dữ liệu trong ONDUTY và OFFDUTY.")
