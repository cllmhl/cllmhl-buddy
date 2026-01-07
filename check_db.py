import sqlite3

conn = sqlite3.connect("buddy_memory.db")
cursor = conn.cursor()

print("--- STORIA (Ultime 5) ---")
for row in cursor.execute("SELECT id, role, text, processed FROM history ORDER BY id DESC LIMIT 5"):
    print(row)

print("\n--- RICORDI DISTILLATI ---")
for row in cursor.execute("SELECT * FROM memories"):
    print(row)

conn.close()