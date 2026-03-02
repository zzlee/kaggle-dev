import sqlite3
import csv
import os

DB_FILE = 'sherds.db'
CSV_FILE = 'h690/jd_sherds_info.csv'
SQL_FILE = 'create_table.sql'

def main():
    # Connect to the SQLite database
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Read and execute the SQL script to create the table
    if os.path.exists(SQL_FILE):
        with open(SQL_FILE, 'r', encoding='utf-8') as sql_file:
            cursor.executescript(sql_file.read())
        print(f"Table 'sherd_info' created successfully in {DB_FILE}")
    else:
        print(f"Error: {SQL_FILE} not found.")
        return

    # Read the CSV file and insert its data
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as csv_file:
            reader = csv.reader(csv_file)
            headers = next(reader) # Extract and skip headers
            
            insert_query = f'''
                INSERT OR REPLACE INTO sherd_info ({", ".join(headers)})
                VALUES ({", ".join(["?" for _ in headers])})
            '''
            
            # Insert all rows
            cursor.executemany(insert_query, reader)
            print(f"Data successfully imported from {CSV_FILE} into {DB_FILE}")
            
    except FileNotFoundError:
        print(f"Error: {CSV_FILE} not found.")

    # Commit changes and close connection
    conn.commit()
    conn.close()

if __name__ == '__main__':
    main()
