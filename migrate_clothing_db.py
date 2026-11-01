import sqlite3
from pathlib import Path


# ============================================================
# DATABASE PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = (
    BASE_DIR
    / "storage"
    / "database"
    / "ai_style.db"
)


# ============================================================
# NEW CLOTHING COLUMNS
# ============================================================

NEW_COLUMNS = {
    "age_group": "TEXT",
    "material": "TEXT",
    "season": "TEXT",
    "available_sizes": "TEXT",
    "brand": "TEXT",
    "product_url": "TEXT",
    "description": "TEXT",
}


# ============================================================
# DATABASE MIGRATION
# ============================================================

def migrate_database():

    print("=" * 60)
    print("UPGRADING CLOTHING DATABASE")
    print("=" * 60)

    if not DB_PATH.exists():
        print("ERROR: Database file was not found.")
        print(f"Expected location: {DB_PATH}")
        return

    connection = sqlite3.connect(DB_PATH)

    try:

        # ----------------------------------------------------
        # Get existing columns
        # ----------------------------------------------------

        existing_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(clothing)"
            ).fetchall()
        }

        print("\nExisting clothing columns:")

        for column in sorted(existing_columns):
            print(f"  * {column}")

        # ----------------------------------------------------
        # Add missing columns
        # ----------------------------------------------------

        print("\nChecking new columns...")

        for column_name, column_type in NEW_COLUMNS.items():

            if column_name in existing_columns:

                print(
                    f"  * {column_name} already exists"
                )

            else:

                connection.execute(
                    f"""
                    ALTER TABLE clothing
                    ADD COLUMN {column_name} {column_type}
                    """
                )

                print(
                    f"  + Added: {column_name}"
                )

        connection.commit()

        # ----------------------------------------------------
        # Verify final structure
        # ----------------------------------------------------

        final_columns = connection.execute(
            "PRAGMA table_info(clothing)"
        ).fetchall()

        print("\n" + "=" * 60)
        print("FINAL CLOTHING TABLE")
        print("=" * 60)

        for row in final_columns:

            print(
                f"{row[0]:>2} | "
                f"{row[1]:<25} | "
                f"{row[2]}"
            )

        # ----------------------------------------------------
        # Count records
        # ----------------------------------------------------

        total = connection.execute(
            "SELECT COUNT(*) FROM clothing"
        ).fetchone()[0]

        print("\n" + "=" * 60)
        print(
            f"Existing clothing records preserved: {total}"
        )
        print("=" * 60)

        print(
            "\nClothing database upgrade completed successfully."
        )

    finally:

        connection.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    migrate_database()