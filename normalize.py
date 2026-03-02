import sqlite3
import os

DB_PATH = 'sherds.db'

def normalize_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. Create lookup tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS units (
        unit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        name_chinese TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parts (
        part_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        name_chinese TEXT
    )""")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS types (
        type_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        name_chinese TEXT
    )""")
    
    # 2. Populate lookup tables from current sherd_info
    for table, col in [('units', 'unit'), ('parts', 'part'), ('types', 'type')]:
        cursor.execute(f"SELECT DISTINCT {col}, {col}_C FROM sherd_info WHERE {col} IS NOT NULL")
        pairs = cursor.fetchall()
        for eng, chi in pairs:
            cursor.execute(f"INSERT OR IGNORE INTO {table} (name, name_chinese) VALUES (?, ?)", (eng, chi))
            
    # 3. Create normalized sherd_info
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sherd_info_new (
        image_id TEXT PRIMARY KEY,
        sherd_id TEXT,
        unit_id INTEGER,
        part_id INTEGER,
        type_id INTEGER,
        image_side TEXT,
        image_id_original TEXT,
        FOREIGN KEY (unit_id) REFERENCES units(unit_id),
        FOREIGN KEY (part_id) REFERENCES parts(part_id),
        FOREIGN KEY (type_id) REFERENCES types(type_id)
    )""")
    
    # 4. Migrate data
    cursor.execute("""
    INSERT INTO sherd_info_new (image_id, sherd_id, unit_id, part_id, type_id, image_side, image_id_original)
    SELECT 
        s.image_id, 
        s.sherd_id, 
        u.unit_id, 
        p.part_id, 
        t.type_id, 
        s.image_side, 
        s.image_id_original
    FROM sherd_info s
    LEFT JOIN units u ON s.unit = u.name
    LEFT JOIN parts p ON s.part = p.name
    LEFT JOIN types t ON s.type = t.name
    """)
    
    # 5. Replace old table
    cursor.execute("DROP TABLE sherd_info")
    cursor.execute("ALTER TABLE sherd_info_new RENAME TO sherd_info")
    
    conn.commit()
    conn.close()
    print("Database normalization complete!")

if __name__ == "__main__":
    normalize_db()
