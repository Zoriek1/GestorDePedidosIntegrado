import os
import sqlite3

# Path to database
db_path = os.path.join(os.path.dirname(__file__), 'database.db')

print(f"Connecting to database at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check existing columns
    cursor.execute("PRAGMA table_info(pedidos)")
    columns = [info[1] for info in cursor.fetchall()]
    print(f"Existing columns: {columns}")

    # Add fonte_pedido if missing
    if 'fonte_pedido' not in columns:
        print("Adding column 'fonte_pedido'...")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN fonte_pedido VARCHAR(50)")
        print("Column 'fonte_pedido' added.")
    else:
        print("Column 'fonte_pedido' already exists.")

    # Add status_pagamento if missing
    if 'status_pagamento' not in columns:
        print("Adding column 'status_pagamento'...")
        cursor.execute("ALTER TABLE pedidos ADD COLUMN status_pagamento VARCHAR(50)")
        print("Column 'status_pagamento' added.")
    else:
        print("Column 'status_pagamento' already exists.")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

except Exception as e:
    print(f"Error during migration: {e}")
