import sqlite3

def clear_daily_bars(db_path):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Execute the DELETE statement to clear the table
        cursor.execute("DELETE FROM daily_bars;")

        # Commit the changes
        conn.commit()

        # Optionally, execute VACUUM to reclaim space
        cursor.execute("VACUUM;")
 
        print("Data cleared successfully from daily_bars table.")
 
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        # Close the database connection
        if conn:
            conn.close()


if __name__ == "__main__":
    db_path = 'stock_data.db'
    clear_daily_bars(db_path)
