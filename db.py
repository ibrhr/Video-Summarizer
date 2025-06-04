import sqlite3

# Global connection
conn = sqlite3.connect("my_bot.db", check_same_thread=False)
cursor = conn.cursor()

def setup_database():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        tier TEXT CHECK(tier IN ('free', 'pro', 'plus')) DEFAULT 'free'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        request_type TEXT CHECK(request_type IN ('Summarize', 'Takeaways', 'Questions')),
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)
    conn.commit()

# Save user data
def save_user(user, tier='free'):
    cursor.execute("""
    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, tier)
    VALUES (?, ?, ?, ?, ?)
    """, (user.id, user.username, user.first_name, user.last_name, tier))
    conn.commit()

    
def log_request(user, request_type):
    # Ensure user is in DB
    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
    VALUES (?, ?, ?, ?)
    """, (user.id, user.username, user.first_name, user.last_name))

    # Log the request
    cursor.execute("""
    INSERT INTO requests (user_id, request_type)
    VALUES (?, ?)
    """, (user.id, request_type))

    conn.commit()
    
def update_user_tier(user_id, new_tier):
    if new_tier not in ['free', 'pro', 'plus']:
        raise ValueError("Invalid tier specified.")
    
    cursor.execute("""
    UPDATE users
    SET tier = ?
    WHERE user_id = ?
    """, (new_tier, user_id))
    conn.commit()
    
def get_user_tier(user_id):
    cursor.execute("""
    SELECT tier FROM users
    WHERE user_id = ?
    """, (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

def get_user_requests(user_id):
    cursor.execute("""
    SELECT request_type, timestamp FROM requests
    WHERE user_id = ?
    ORDER BY timestamp DESC
    """, (user_id,))
    return cursor.fetchall()

# add request
def add_request(user_id, request_type):
    if request_type not in ['Summarize', 'Takeaways', 'Questions']:
        raise ValueError("Invalid request type specified.")
    
    cursor.execute("""
    INSERT INTO requests (user_id, request_type)
    VALUES (?, ?)
    """, (user_id, request_type))
    conn.commit()
    
# get number of requests made by the user today
def get_requests_today(user_id):
    cursor.execute("""
    SELECT COUNT(*) FROM requests
    WHERE user_id = ? AND DATE(timestamp) = DATE('now')
    """, (user_id,))
    result = cursor.fetchone()
    return result[0] if result else 0