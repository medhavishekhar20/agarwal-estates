import sqlite3
import pandas as pd

def import_all_data():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # 1. Load the Excel Dataset
    try:
        df_excel = pd.read_excel('AE Project_Property Details_22Jul26 (1).xlsx')
        # Standardize your column names here if needed
        df_excel.to_sql('properties', conn, if_exists='replace', index=False)
        print("Excel dataset imported successfully!")
    except FileNotFoundError:
        print("Warning: Excel file not found. Skipping...")

    # 2. Load the Bengaluru House Dataset
    try:
        df_csv = pd.read_csv('Bengaluru_House_Data.csv') # Adjust filename if it has an extension like .csv
        df_csv.to_sql('bengaluru_data', conn, if_exists='replace', index=False)
        print("Bengaluru housing dataset imported successfully!")
    except FileNotFoundError:
        print("Warning: Bengaluru CSV file not found. Skipping...")
        
    conn.close()

if __name__ == "__main__":
    import_all_data()