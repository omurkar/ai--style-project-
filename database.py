import sqlite3
from pathlib import Path


# Project root directory
BASE_DIR = Path(__file__).resolve().parent

# Database directory
DATABASE_DIR = BASE_DIR / "storage" / "database"

# Create directory if it does not exist
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# SQLite database path
DATABASE_PATH = DATABASE_DIR / "ai_style.db"


def get_connection():
    """
    Create and return a connection to the SQLite database.
    """

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    # Allows database rows to behave like dictionaries
    connection.row_factory = sqlite3.Row

    # Enable foreign-key relationships
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialize_database():
    """
    Create all required database tables.
    """

    connection = get_connection()

    cursor = connection.cursor()


    # =========================
    # USERS TABLE
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            full_name TEXT NOT NULL,

            email TEXT NOT NULL UNIQUE,

            password_hash TEXT NOT NULL,

            category TEXT,

            age INTEGER,

            role TEXT DEFAULT 'user',

            firebase_uid TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # Migration for existing users table
    cursor.execute("PRAGMA table_info(users)")
    existing_user_cols = [row[1] for row in cursor.fetchall()]
    if "role" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    if "firebase_uid" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN firebase_uid TEXT")
    if "profile_photo" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN profile_photo TEXT")
    if "face_template" not in existing_user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN face_template TEXT")


    # =========================
    # USER STYLE PROFILES
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS style_profiles (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL UNIQUE,

            skin_tone TEXT,

            undertone TEXT,

            body_shape TEXT,

            body_proportions TEXT,

            height_cm REAL,

            preferred_style TEXT,

            preferred_occasion TEXT,

            preferred_colours TEXT,

            budget REAL,

            analysis_status TEXT DEFAULT 'pending',

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
    """)


    # Migration for existing style_profiles table
    cursor.execute("PRAGMA table_info(style_profiles)")
    existing_profile_cols = [row[1] for row in cursor.fetchall()]
    if "face_template" not in existing_profile_cols:
        cursor.execute("ALTER TABLE style_profiles ADD COLUMN face_template TEXT")
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clothing (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            outfit_id TEXT NOT NULL UNIQUE,

            outfit_name TEXT NOT NULL,

            category TEXT NOT NULL,

            clothing_type TEXT,

            colour TEXT,

            pattern TEXT,

            style TEXT,

            occasion TEXT,

            fit TEXT,

            suitable_body_shapes TEXT,

            suitable_skin_tones TEXT,

            suitable_undertones TEXT,

            suitable_proportion_types TEXT,

            min_height_cm REAL,

            max_height_cm REAL,

            image_path TEXT,

            tryon_image_path TEXT,

            product_store TEXT,

            price REAL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            age_group TEXT,

            material TEXT,

            season TEXT,

            available_sizes TEXT,

            brand TEXT,

            product_url TEXT,

            description TEXT,

            face_target TEXT

        )
    """)

    # Migration for existing clothing table
    cursor.execute("PRAGMA table_info(clothing)")
    existing_clothing_cols = [row[1] for row in cursor.fetchall()]
    if "face_target" not in existing_clothing_cols:
        cursor.execute("ALTER TABLE clothing ADD COLUMN face_target TEXT")


    # =========================
    # FAVOURITES TABLE
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favourites (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            clothing_id INTEGER NOT NULL,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(user_id, clothing_id),

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (clothing_id)
                REFERENCES clothing(id)
                ON DELETE CASCADE

        )
    """)


    # =========================
    # TRY-ON RESULTS TABLE
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tryon_results (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            clothing_id INTEGER NOT NULL,

            original_photo_path TEXT,

            result_photo_path TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (clothing_id)
                REFERENCES clothing(id)
                ON DELETE CASCADE

        )
    """)


    # =========================
    # ORDERS TABLE
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            order_id TEXT NOT NULL UNIQUE,

            user_id INTEGER,

            user_email TEXT,

            clothing_id INTEGER,

            product_name TEXT,

            size TEXT,

            quantity INTEGER DEFAULT 1,

            price REAL,

            delivery_name TEXT,

            delivery_phone TEXT,

            delivery_address_line1 TEXT,

            delivery_address_line2 TEXT,

            delivery_city TEXT,

            delivery_state TEXT,

            delivery_postal_code TEXT,

            latitude REAL,

            longitude REAL,

            location_accuracy REAL,

            payment_method TEXT DEFAULT 'UPI',

            payment_status TEXT DEFAULT 'PENDING',

            upi_reference_id TEXT,

            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (clothing_id)
                REFERENCES clothing(id)
                ON DELETE SET NULL

        )
    """)


    # =========================
    # SETTINGS TABLE
    # =========================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (

            key TEXT PRIMARY KEY,

            value TEXT,

            updated_at TEXT DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # Seed default Master Google Pay UPI settings
    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('master_upi_id', 'merchant@okhdfcbank')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO settings (key, value)
        VALUES ('merchant_name', 'AI Style Fashion Store')
    """)

    # Seed default Admin and Demo user
    from security.auth import hash_password
    admin_hash = hash_password("admin123")
    user_hash = hash_password("user123")

    cursor.execute("""
        INSERT OR IGNORE INTO users (full_name, email, password_hash, role, category)
        VALUES ('Store Administrator', 'admin@aistyle.com', ?, 'admin', 'Unisex')
    """, (admin_hash,))

    cursor.execute("""
        INSERT OR IGNORE INTO users (full_name, email, password_hash, role, category)
        VALUES ('Fashion Explorer', 'user@aistyle.com', ?, 'user', 'Women')
    """, (user_hash,))

    connection.commit()

    connection.close()


if __name__ == "__main__":

    initialize_database()

    print("Database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")