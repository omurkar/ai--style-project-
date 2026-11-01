"""
Local Clothing Asset Database
----------------------------
Manages local physical file storage and database records for clothing items.
Stores clothing packshots and virtual try-on assets locally in `storage/clothing/`
and indexes metadata in SQLite `clothing` table.
"""

import os
import time
from pathlib import Path
from werkzeug.utils import secure_filename
from database import get_connection

BASE_DIR = Path(__file__).resolve().parent
CLOTHING_STORAGE_DIR = BASE_DIR / "storage" / "clothing"
CLOTHING_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


class LocalClothingAssetDB:
    """
    Local Asset Database for clothing images and metadata.
    """

    @staticmethod
    def get_clothing_dir():
        CLOTHING_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        return CLOTHING_STORAGE_DIR

    @classmethod
    def save_clothing_file(cls, file_obj, prefix="garment"):
        """
        Save an uploaded image file directly to the local clothing storage directory.
        Returns the relative path e.g. 'storage/clothing/filename.jpg' and the absolute Path.
        """
        cls.get_clothing_dir()
        original_name = getattr(file_obj, "filename", "clothing.jpg")
        clean_name = secure_filename(original_name) or "clothing.jpg"
        
        timestamp = int(time.time() * 1000)
        filename = f"{prefix}_{timestamp}_{clean_name}"
        destination = CLOTHING_STORAGE_DIR / filename

        if hasattr(file_obj, "save"):
            file_obj.save(str(destination))
        elif isinstance(file_obj, (bytes, bytearray)):
            with open(destination, "wb") as f:
                f.write(file_obj)

        relative_path = f"storage/clothing/{filename}"
        return relative_path, destination

    @classmethod
    def create_clothing_record(cls, data, clothing_file=None, tryon_file=None):
        """
        Store clothing image(s) locally and insert a complete product record into the database.
        """
        image_path = data.get("image_path", "")
        tryon_image_path = data.get("tryon_image_path", "")

        # Save files locally if provided
        if clothing_file and getattr(clothing_file, "filename", None):
            rel_path, _ = cls.save_clothing_file(clothing_file, prefix="item")
            image_path = rel_path

        if tryon_file and getattr(tryon_file, "filename", None):
            rel_path, _ = cls.save_clothing_file(tryon_file, prefix="tryon")
            tryon_image_path = rel_path

        if not tryon_image_path and image_path:
            tryon_image_path = image_path

        outfit_id = data.get("outfit_id") or f"LOC_{int(time.time() * 1000) % 100000}"
        outfit_name = data.get("outfit_name", "Clothing Item")
        category = data.get("category", "Unisex")
        clothing_type = data.get("clothing_type", "Top")
        colour = data.get("colour", "")
        price = float(data.get("price") or 0.0)
        sizes = data.get("available_sizes", "S,M,L,XL")
        if isinstance(sizes, list):
            sizes = ",".join(sizes)
        brand = data.get("brand", "AI Style")
        description = data.get("description", "")
        fit = data.get("fit", "")

        conn = get_connection()
        try:
            cursor = conn.execute("""
                INSERT INTO clothing (
                    outfit_id, outfit_name, category, clothing_type, colour,
                    price, available_sizes, brand, description, fit,
                    image_path, tryon_image_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                outfit_id, outfit_name, category, clothing_type, colour,
                price, sizes, brand, description, fit,
                image_path, tryon_image_path
            ))
            product_id = cursor.lastrowid
            conn.commit()

            row = conn.execute("SELECT * FROM clothing WHERE id = ?", (product_id,)).fetchone()
            item = dict(row)
            item["sizes_list"] = [s.strip() for s in (item.get("available_sizes") or "").split(",") if s.strip()]
            return item
        finally:
            conn.close()

    @classmethod
    def get_all_local_clothing(cls):
        """
        List all clothing items stored in the local database.
        """
        conn = get_connection()
        try:
            rows = conn.execute("SELECT * FROM clothing ORDER BY id DESC").fetchall()
            items = [dict(r) for r in rows]
            for it in items:
                raw_sizes = it.get("available_sizes") or ""
                it["sizes_list"] = [s.strip() for s in raw_sizes.split(",") if s.strip()] or ["XS", "S", "M", "L", "XL"]
            return items
        finally:
            conn.close()

    @classmethod
    def get_clothing_by_id(cls, clothing_id):
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM clothing WHERE id = ? OR outfit_id = ?",
                (clothing_id, str(clothing_id))
            ).fetchone()
            if not row:
                return None
            it = dict(row)
            raw_sizes = it.get("available_sizes") or ""
            it["sizes_list"] = [s.strip() for s in raw_sizes.split(",") if s.strip()] or ["XS", "S", "M", "L", "XL"]
            return it
        finally:
            conn.close()

    @classmethod
    def delete_clothing(cls, clothing_id):
        """
        Delete clothing record from local database and remove physical image files from disk.
        """
        item = cls.get_clothing_by_id(clothing_id)
        if not item:
            return False

        # Attempt to remove local file if stored locally
        for key in ["image_path", "tryon_image_path"]:
            p = item.get(key)
            if p and p.startswith("storage/"):
                abs_file = BASE_DIR / p
                if abs_file.exists() and abs_file.is_file():
                    try:
                        abs_file.unlink()
                    except Exception as e:
                        print(f"[Local Asset DB] Could not remove file {abs_file}: {e}")

        conn = get_connection()
        try:
            conn.execute("DELETE FROM clothing WHERE id = ?", (item["id"],))
            conn.commit()
            return True
        finally:
            conn.close()

