import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kino_bot.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admins (
        user_id INTEGER PRIMARY KEY,
        full_name TEXT,
        username TEXT,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS movies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        file_id TEXT NOT NULL,
        description TEXT,
        views INTEGER DEFAULT 0,
        added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_id TEXT UNIQUE NOT NULL,
        channel_url TEXT NOT NULL,
        title TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()

def add_admin(user_id: int, full_name: str = "", username: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (user_id, full_name, username) VALUES (?, ?, ?)", (user_id, full_name, username))
    conn.commit()
    conn.close()

def is_admin(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    cursor.execute("SELECT COUNT(*) FROM admins")
    total = cursor.fetchone()[0]
    conn.close()
    if total == 0:
        add_admin(user_id)
        return True
    return row is not None

def get_admins():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM admins")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def add_user(user_id: int, full_name: str, username: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)", (user_id, full_name, username))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_users_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def add_movie(code: str, title: str, file_id: str, description: str = ""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO movies (code, title, file_id, description) VALUES (?, ?, ?, ?)", (code.strip(), title.strip(), file_id.strip(), description.strip()))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    conn.close()
    return success

def get_movie_by_code(code: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, code, title, file_id, description, views FROM movies WHERE code = ?", (code.strip(),))
    movie = cursor.fetchone()
    if movie:
        cursor.execute("UPDATE movies SET views = views + 1 WHERE id = ?", (movie[0],))
        conn.commit()
    conn.close()
    return movie

def search_movies_by_title(query: str, limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT code, title FROM movies WHERE title LIKE ? LIMIT ?", (f"%{query}%", limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_movies_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_latest_movies(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT code, title, views FROM movies ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_top_movies(limit: int = 5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT code, title, views FROM movies ORDER BY views DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_movies_list(page: int = 1, per_page: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM movies")
    total_count = cursor.fetchone()[0]
    offset = (page - 1) * per_page
    cursor.execute("SELECT id, code, title, views, added_date FROM movies ORDER BY id DESC LIMIT ? OFFSET ?", (per_page, offset))
    rows = cursor.fetchall()
    conn.close()
    return rows, total_count

def delete_movie_by_code(code: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE code = ?", (code.strip(),))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_channels():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_url, title FROM channels")
    rows = cursor.fetchall()
    conn.close()
    return rows

def add_channel(channel_id: str, channel_url: str, title: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO channels (channel_id, channel_url, title) VALUES (?, ?, ?)", (channel_id.strip(), channel_url.strip(), title.strip()))
        conn.commit()
        success = True
    except Exception:
        success = False
    conn.close()
    return success

def delete_channel(channel_id: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id.strip(),))
    conn.commit()
    conn.close()
