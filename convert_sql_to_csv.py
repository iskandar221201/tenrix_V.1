import os
import sys
import pandas as pd
import duckdb

# Menambahkan directory project ke sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from core.connectors import _clean_sql_dump, _split_sql_statements

def main():
    # Menggunakan path absolut yang valid
    sql_path = r"c:\Users\USER\Pictures\a\orca.sql"
    output_dir = os.path.dirname(os.path.abspath(__file__)) # Simpan di folder yang sama dengan script (workspace)
    
    print(f"Reading {sql_path}...")
    try:
        with open(sql_path, "r", encoding="utf-8", errors="replace") as f:
            sql_text = f.read()
    except Exception as e:
        print(f"Error reading SQL: {e}")
        return
    
    print("Cleaning and splitting SQL...")
    cleaned = _clean_sql_dump(sql_text)
    statements = _split_sql_statements(cleaned)
    
    print(f"Executing {len(statements)} statements in DuckDB...")
    
    # Debug: simpan statements ke file untuk pengecekan
    with open(os.path.join(output_dir, "debug_statements.txt"), "w", encoding="utf-8") as debug_f:
        for i, s in enumerate(statements[:50]): # Cek 50 pertama
            debug_f.write(f"--- STATEMENT {i} ---\n{s}\n\n")

    con = duckdb.connect()
    
    loaded = 0
    errors = 0
    for stmt in statements:
        stmt = stmt.strip()
        if not stmt: continue
        
        # Lebih toleran terhadap whitespace di awal
        upper_lstrip = stmt.upper().lstrip()
        if not (upper_lstrip.startswith("CREATE TABLE") or upper_lstrip.startswith("INSERT INTO")):
            continue
        try:
            con.execute(stmt)
            loaded += 1
        except Exception as e:
            errors += 1
            # Safely report error without crashing on Unicode
            safe_stmt = stmt[:100].replace("\n", " ")
            try:
                print(f"Error executing statement: {e}\nStmt: {safe_stmt}...")
            except UnicodeEncodeError:
                # If still failing, print just the error message and a sanitized statement
                sanitized_e = str(e).encode('ascii', 'ignore').decode('ascii')
                print(f"Error executing statement: {sanitized_e}")
                print(f"Stmt (sanitized): {safe_stmt.encode('ascii', 'ignore').decode('ascii')}...")
            
    print(f"Successfully loaded {loaded} statements. Errors: {errors}")
            
    # List tables
    tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'").fetchall()
    tables = [t[0] for t in tables]
    
    print(f"Found {len(tables)} tables. Exporting to CSV...")
    
    for table in tables:
        csv_filename = f"{table}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        print(f"  Exporting {table} -> {csv_filename}...")
        try:
            con.execute(f"COPY \"{table}\" TO '{csv_path}' (HEADER, DELIMITER ',')")
        except Exception as e:
            print(f"  Failed to export {table}: {e}")
            
    print("\nConversion complete!")

if __name__ == "__main__":
    main()
