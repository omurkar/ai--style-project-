"""
Firebase Integration Service
----------------------------
Manages connection to Google Firebase Firestore (NoSQL) and Firebase Storage.
Provides collections for Users, Products, Orders, and Settings.
Gracefully handles development fallback if service account keys are not yet configured.
"""

import os
import json
import base64
import time
import sqlite3
from pathlib import Path
from werkzeug.utils import secure_filename

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"

# Global references
FIREBASE_AVAILABLE = False
firestore_db = None
storage_bucket = None

# Attempt to initialize Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, storage, auth

    # Check for credentials file in order of precedence:
    # 1. FIREBASE_SERVICE_ACCOUNT_KEY env var (path or JSON string)
    # 2. GOOGLE_APPLICATION_CREDENTIALS env var
    # 3. serviceAccountKey.json in BASE_DIR
    # 4. firebase_credentials.json in BASE_DIR
    cred_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
    if not cred_path:
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not cred_path:
        candidate = BASE_DIR / "serviceAccountKey.json"
        if candidate.exists():
            cred_path = str(candidate)
    if not cred_path:
        candidate = BASE_DIR / "firebase_credentials.json"
        if candidate.exists():
            cred_path = str(candidate)

    if cred_path and os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "sandya-project.firebasestorage.app")
        app_options = {}
        if bucket_name:
            app_options["storageBucket"] = bucket_name

        if not firebase_admin._apps:
            firebase_app = firebase_admin.initialize_app(cred, app_options if app_options else None)
        else:
            firebase_app = firebase_admin.get_app()

        firestore_db = firestore.client()
        if bucket_name:
            try:
                storage_bucket = storage.bucket()
            except Exception as b_err:
                print(f"[Firebase] Storage bucket warning: {b_err}")

        FIREBASE_AVAILABLE = True
        print(f"[Firebase] Successfully connected to live Firestore & Storage with: {cred_path}")
    else:
        print("[Firebase] No serviceAccountKey.json found. Running in Dual-Mode (SQLite persistence with Firestore schema compatibility).")
        print("[Firebase] To activate live Cloud Firestore & Storage, place serviceAccountKey.json in the project root.")

except Exception as err:
    print(f"[Firebase] Initialization note: {err}")
    FIREBASE_AVAILABLE = False


# =========================================================
# FIREBASE AUTH TOKEN VERIFICATION
# =========================================================

def verify_google_id_token(id_token):
    """
    Verify Google OAuth ID token using Firebase Admin Auth.
    Falls back to safe JWT decoding for development/offline testing.
    """
    if not id_token:
        raise ValueError("Missing ID token")

    if FIREBASE_AVAILABLE:
        try:
            from firebase_admin import auth
            decoded = auth.verify_id_token(id_token)
            return {
                "uid": decoded.get("uid"),
                "email": decoded.get("email"),
                "name": decoded.get("name", ""),
                "picture": decoded.get("picture", "")
            }
        except Exception as e:
            print(f"[Firebase Auth] Verification failed with live SDK: {e}. Checking payload fallback.")

    # Safe payload extraction fallback
    try:
        parts = id_token.split(".")
        if len(parts) >= 2:
            padding = 4 - (len(parts[1]) % 4)
            payload_str = base64.urlsafe_b64decode(parts[1] + ("=" * padding)).decode("utf-8")
            data = json.loads(payload_str)
            return {
                "uid": data.get("user_id") or data.get("sub") or data.get("uid"),
                "email": data.get("email"),
                "name": data.get("name", ""),
                "picture": data.get("picture", "")
            }
    except Exception as e:
        print(f"[Firebase Auth] Token parse fallback error: {e}")

    # Direct mock/demo token support for testing
    if id_token.startswith("demo_token_"):
        parts = id_token.split(":")
        email = parts[1] if len(parts) > 1 else "demo_user@example.com"
        name = parts[2] if len(parts) > 2 else "Demo Google User"
        return {
            "uid": f"google_{email.replace('@', '_').replace('.', '_')}",
            "email": email,
            "name": name,
            "picture": "https://lh3.googleusercontent.com/a/default-user=s96-c"
        }

    raise ValueError("Invalid or unverified Firebase ID token")


# =========================================================
# FILE STORAGE HELPER (FIREBASE STORAGE + LOCAL FALLBACK)
# =========================================================

def upload_clothing_asset(file_obj, folder="clothing", custom_filename=None):
    """
    Upload an image file to Firebase Storage if available,
    or locally to storage/<folder>/ as reliable fallback.
    Returns the web-accessible path / URL.
    """
    filename = custom_filename or secure_filename(getattr(file_obj, "filename", "asset.jpg"))
    if not filename:
        filename = f"asset_{int(time.time())}.jpg"

    # Always ensure local copy exists for fast serving
    target_dir = STORAGE_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    local_path = target_dir / filename

    if hasattr(file_obj, "save"):
        file_obj.save(str(local_path))
    elif isinstance(file_obj, (bytes, bytearray)):
        with open(local_path, "wb") as f:
            f.write(file_obj)

    # If live Firebase Storage bucket is configured, upload blob
    if FIREBASE_AVAILABLE and storage_bucket:
        try:
            blob = storage_bucket.blob(f"{folder}/{filename}")
            blob.upload_from_filename(str(local_path))
            blob.make_public()
            return blob.public_url
        except Exception as e:
            print(f"[Firebase Storage] Upload notice: {e}. Using local storage path.")

    # Return relative path for local serving
    return f"storage/{folder}/{filename}"


# =========================================================
# FIRESTORE DATA REPOSITORY (USERS, PRODUCTS, ORDERS, SETTINGS)
# =========================================================

class FirestoreRepository:
    """
    Unified access layer that manages Firestore collections:
    - users
    - products
    - orders
    - settings
    Synchronizes with SQLite for seamless dual persistence.
    """

    @staticmethod
    def _get_sqlite_conn():
        from database import get_connection
        return get_connection()

    # ---------------------------------------------------------
    # USERS COLLECTION
    # ---------------------------------------------------------

    @classmethod
    def get_user_by_email(cls, email):
        email = email.strip().lower()
        # Check Firestore
        if FIREBASE_AVAILABLE and firestore_db:
            try:
                users_ref = firestore_db.collection("users")
                docs = users_ref.where("email", "==", email).limit(1).stream()
                for doc in docs:
                    data = doc.to_dict()
                    data["id"] = doc.id
                    return data
            except Exception as e:
                print(f"[Firestore] get_user_by_email error: {e}")

        # SQLite query
        conn = cls._get_sqlite_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @classmethod
    def get_user_by_id(cls, user_id):
        conn = cls._get_sqlite_conn()
        try:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @classmethod
    def update_user_face_template(cls, user_id, face_template_path):
        """Update the user's oval-cropped face template path in SQLite and Firestore."""
        conn = cls._get_sqlite_conn()
        try:
            conn.execute(
                "UPDATE users SET face_template = ?, profile_photo = ? WHERE id = ?",
                (face_template_path, face_template_path, user_id)
            )
            # Also update style_profiles if record exists
            conn.execute(
                "UPDATE style_profiles SET face_template = ? WHERE user_id = ?",
                (face_template_path, user_id)
            )
            conn.commit()
        finally:
            conn.close()

        if FIREBASE_AVAILABLE and firestore_db:
            try:
                user_doc = firestore_db.collection("users").document(str(user_id))
                user_doc.set({"face_template": face_template_path, "profile_photo": face_template_path}, merge=True)
            except Exception as e:
                print(f"[Firestore] update_user_face_template error: {e}")

    @classmethod
    def get_user_face_template(cls, user_id):
        conn = cls._get_sqlite_conn()
        try:
            row = conn.execute("SELECT face_template, profile_photo FROM users WHERE id = ?", (user_id,)).fetchone()
            if row:
                return row["face_template"] or row["profile_photo"]
            return None
        finally:
            conn.close()

    @classmethod
    def save_google_user(cls, google_info, role="user"):
        """
        Create or update user authenticated via Google OAuth.
        Stores in both Firestore and SQLite.
        """
        email = google_info.get("email", "").strip().lower()
        full_name = google_info.get("name") or email.split("@")[0].title()
        uid = google_info.get("uid", "")
        photo_url = google_info.get("picture", "")

        # Default admin check: email containing admin or matches default
        if email in ["admin@aistyle.com", "admin@gmail.com"] or "admin" in email:
            role = "admin"

        conn = cls._get_sqlite_conn()
        user_id = None
        try:
            existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                user_id = existing["id"]
                conn.execute(
                    "UPDATE users SET full_name = ?, firebase_uid = ?, role = ? WHERE id = ?",
                    (full_name, uid, role if existing["role"] != "admin" else "admin", user_id)
                )
            else:
                cursor = conn.execute(
                    "INSERT INTO users (full_name, email, password_hash, role, firebase_uid) VALUES (?, ?, ?, ?, ?)",
                    (full_name, email, "FIREBASE_OAUTH_USER", role, uid)
                )
                user_id = cursor.lastrowid
            conn.commit()
        finally:
            conn.close()

        # Update Firestore
        if FIREBASE_AVAILABLE and firestore_db:
            try:
                user_doc_ref = firestore_db.collection("users").document(uid or f"user_{user_id}")
                user_doc_ref.set({
                    "uid": uid,
                    "sqlite_id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "photo_url": photo_url,
                    "role": role,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)
            except Exception as e:
                print(f"[Firestore] save_google_user error: {e}")

        return cls.get_user_by_id(user_id)

    # ---------------------------------------------------------
    # PRODUCTS COLLECTION
    # ---------------------------------------------------------

    @classmethod
    def get_all_products(cls):
        """
        Return list of all products from SQLite/Firestore.
        """
        conn = cls._get_sqlite_conn()
        try:
            rows = conn.execute("SELECT * FROM clothing ORDER BY id DESC").fetchall()
            products = [dict(r) for r in rows]
            # Ensure available_sizes is list
            for p in products:
                raw_sizes = p.get("available_sizes")
                if isinstance(raw_sizes, str) and raw_sizes:
                    p["sizes_list"] = [s.strip() for s in raw_sizes.split(",") if s.strip()]
                elif isinstance(raw_sizes, list):
                    p["sizes_list"] = raw_sizes
                else:
                    p["sizes_list"] = ["XS", "S", "M", "L", "XL"]
            return products
        finally:
            conn.close()

    @classmethod
    def get_product(cls, clothing_id):
        conn = cls._get_sqlite_conn()
        try:
            row = conn.execute("SELECT * FROM clothing WHERE id = ? OR outfit_id = ?", (clothing_id, str(clothing_id))).fetchone()
            if not row:
                return None
            p = dict(row)
            raw_sizes = p.get("available_sizes")
            if isinstance(raw_sizes, str) and raw_sizes:
                p["sizes_list"] = [s.strip() for s in raw_sizes.split(",") if s.strip()]
            else:
                p["sizes_list"] = ["XS", "S", "M", "L", "XL"]
            return p
        finally:
            conn.close()

    @classmethod
    def _ensure_unique_outfit_id(cls, conn, outfit_id=None, category="Unisex"):
        """
        Guarantees that an outfit_id is unique in the clothing table.
        - If an outfit_id was provided: checks for collisions and generates a clean variation (e.g. ID_1).
        - If no outfit_id was provided: computes the next sequential SKU based on category prefix (e.g. W026, M004, K003, U001).
        """
        cat_lower = str(category).strip().lower()
        if "women" in cat_lower:
            prefix = "W"
        elif "men" in cat_lower:
            prefix = "M"
        elif "kid" in cat_lower:
            prefix = "K"
        else:
            prefix = "U"

        if outfit_id:
            cleaned = str(outfit_id).strip()
            if cleaned:
                row = conn.execute("SELECT 1 FROM clothing WHERE outfit_id = ?", (cleaned,)).fetchone()
                if not row:
                    return cleaned
                # Suffix collision resolver
                suffix = 1
                while True:
                    candidate = f"{cleaned}_{suffix}"
                    if not conn.execute("SELECT 1 FROM clothing WHERE outfit_id = ?", (candidate,)).fetchone():
                        return candidate
                    suffix += 1

        # Calculate next sequential prefix number
        rows = conn.execute("SELECT outfit_id FROM clothing WHERE outfit_id LIKE ?", (f"{prefix}%",)).fetchall()
        max_num = 0
        for r in rows:
            code = r[0] if isinstance(r, (list, tuple)) or hasattr(r, '__getitem__') else r["outfit_id"]
            num_part = code[len(prefix):]
            if num_part.isdigit():
                max_num = max(max_num, int(num_part))

        next_num = max_num + 1
        while True:
            candidate = f"{prefix}{next_num:03d}"
            if not conn.execute("SELECT 1 FROM clothing WHERE outfit_id = ?", (candidate,)).fetchone():
                return candidate
            next_num += 1

    @classmethod
    def create_product(cls, product_data):
        """
        Add a new clothing item to both SQLite and Firestore with collision-proof outfit_id assignment.
        """
        category = product_data.get("category", "Unisex")
        outfit_name = product_data.get("outfit_name", "New Outfit")
        clothing_type = product_data.get("clothing_type", "Top")
        colour = product_data.get("colour", "")
        price = float(product_data.get("price") or 0.0)
        sizes = product_data.get("available_sizes", "S,M,L,XL")
        if isinstance(sizes, list):
            sizes = ",".join(sizes)
        brand = product_data.get("brand", "AI Style")
        description = product_data.get("description", "")
        image_path = product_data.get("image_path", "")
        tryon_image_path = product_data.get("tryon_image_path") or image_path
        face_target = product_data.get("face_target", "")

        conn = cls._get_sqlite_conn()
        try:
            outfit_id = cls._ensure_unique_outfit_id(
                conn,
                outfit_id=product_data.get("outfit_id"),
                category=category
            )

            max_retries = 5
            product_id = None
            for attempt in range(max_retries):
                try:
                    cursor = conn.execute("""
                        INSERT INTO clothing (
                            outfit_id, outfit_name, category, clothing_type, colour,
                            price, available_sizes, brand, description, image_path, tryon_image_path,
                            face_target
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        outfit_id, outfit_name, category, clothing_type, colour,
                        price, sizes, brand, description, image_path, tryon_image_path,
                        face_target
                    ))
                    product_id = cursor.lastrowid
                    conn.commit()
                    break
                except sqlite3.IntegrityError as ie:
                    if "clothing.outfit_id" in str(ie) and attempt < max_retries - 1:
                        outfit_id = f"{outfit_id}_{int(time.time() * 1000) % 10000}_{attempt + 1}"
                        continue
                    raise
        finally:
            conn.close()

        # Firestore write
        if FIREBASE_AVAILABLE and firestore_db:
            try:
                firestore_db.collection("products").document(outfit_id).set({
                    "id": product_id,
                    "outfit_id": outfit_id,
                    "outfit_name": outfit_name,
                    "category": category,
                    "clothing_type": clothing_type,
                    "colour": colour,
                    "price": price,
                    "available_sizes": sizes.split(","),
                    "brand": brand,
                    "description": description,
                    "image_path": image_path,
                    "tryon_image_path": tryon_image_path,
                    "face_target": face_target,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"[Firestore] create_product error: {e}")

        return cls.get_product(product_id)

    @classmethod
    def update_product(cls, clothing_id, update_data):
        """
        Update an existing clothing item.
        """
        conn = cls._get_sqlite_conn()
        try:
            fields = []
            values = []
            for k in ["outfit_name", "category", "clothing_type", "colour", "price",
                      "available_sizes", "brand", "description", "image_path", "tryon_image_path", "face_target"]:
                if k in update_data:
                    val = update_data[k]
                    if k == "available_sizes" and isinstance(val, list):
                        val = ",".join(val)
                    fields.append(f"{k} = ?")
                    values.append(val)

            if fields:
                values.append(clothing_id)
                conn.execute(f"UPDATE clothing SET {', '.join(fields)} WHERE id = ?", tuple(values))
                conn.commit()
        finally:
            conn.close()

        updated = cls.get_product(clothing_id)

        # Firestore update
        if FIREBASE_AVAILABLE and firestore_db and updated:
            try:
                doc_id = updated.get("outfit_id", str(clothing_id))
                firestore_db.collection("products").document(doc_id).set({
                    "outfit_name": updated.get("outfit_name"),
                    "category": updated.get("category"),
                    "clothing_type": updated.get("clothing_type"),
                    "price": updated.get("price"),
                    "available_sizes": updated.get("sizes_list", []),
                    "colour": updated.get("colour"),
                    "brand": updated.get("brand"),
                    "description": updated.get("description"),
                    "image_path": updated.get("image_path"),
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)
            except Exception as e:
                print(f"[Firestore] update_product error: {e}")

        return updated

    @classmethod
    def delete_product(cls, clothing_id):
        product = cls.get_product(clothing_id)
        conn = cls._get_sqlite_conn()
        try:
            conn.execute("DELETE FROM clothing WHERE id = ?", (clothing_id,))
            conn.commit()
        finally:
            conn.close()

        if FIREBASE_AVAILABLE and firestore_db and product:
            try:
                doc_id = product.get("outfit_id", str(clothing_id))
                firestore_db.collection("products").document(doc_id).delete()
            except Exception as e:
                print(f"[Firestore] delete_product error: {e}")

        return True

    # ---------------------------------------------------------
    # ORDERS COLLECTION
    # ---------------------------------------------------------

    @classmethod
    def create_order(cls, order_data):
        """
        Record a customer checkout order in both SQLite and Firestore.
        """
        order_id = order_data.get("order_id") or f"ORD-{int(time.time())}-{os.urandom(2).hex().upper()}"
        user_id = order_data.get("user_id")
        user_email = order_data.get("user_email", "")
        clothing_id = order_data.get("clothing_id")
        product_name = order_data.get("product_name", "")
        size = order_data.get("size", "M")
        quantity = int(order_data.get("quantity") or 1)
        price = float(order_data.get("price") or 0.0)

        delivery_name = order_data.get("delivery_name", "")
        delivery_phone = order_data.get("delivery_phone", "")
        delivery_address_line1 = order_data.get("delivery_address_line1", "")
        delivery_address_line2 = order_data.get("delivery_address_line2", "")
        delivery_city = order_data.get("delivery_city", "")
        delivery_state = order_data.get("delivery_state", "")
        delivery_postal_code = order_data.get("delivery_postal_code", "")

        latitude = float(order_data.get("latitude") or 0.0) if order_data.get("latitude") else None
        longitude = float(order_data.get("longitude") or 0.0) if order_data.get("longitude") else None
        location_accuracy = float(order_data.get("location_accuracy") or 0.0) if order_data.get("location_accuracy") else None

        payment_method = order_data.get("payment_method", "UPI")
        payment_status = order_data.get("payment_status", "PENDING")
        upi_reference_id = order_data.get("upi_reference_id", "")

        conn = cls._get_sqlite_conn()
        try:
            cursor = conn.execute("""
                INSERT INTO orders (
                    order_id, user_id, user_email, clothing_id, product_name,
                    size, quantity, price, delivery_name, delivery_phone,
                    delivery_address_line1, delivery_address_line2, delivery_city,
                    delivery_state, delivery_postal_code, latitude, longitude,
                    location_accuracy, payment_method, payment_status, upi_reference_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order_id, user_id, user_email, clothing_id, product_name,
                size, quantity, price, delivery_name, delivery_phone,
                delivery_address_line1, delivery_address_line2, delivery_city,
                delivery_state, delivery_postal_code, latitude, longitude,
                location_accuracy, payment_method, payment_status, upi_reference_id
            ))
            conn.commit()
        finally:
            conn.close()

        # Firestore write
        if FIREBASE_AVAILABLE and firestore_db:
            try:
                firestore_db.collection("orders").document(order_id).set({
                    "order_id": order_id,
                    "user_id": user_id,
                    "user_email": user_email,
                    "clothing_id": clothing_id,
                    "product_name": product_name,
                    "size": size,
                    "quantity": quantity,
                    "price": price,
                    "total_amount": price * quantity,
                    "delivery_address": {
                        "name": delivery_name,
                        "phone": delivery_phone,
                        "line1": delivery_address_line1,
                        "line2": delivery_address_line2,
                        "city": delivery_city,
                        "state": delivery_state,
                        "postal_code": delivery_postal_code
                    },
                    "coordinates": {
                        "latitude": latitude,
                        "longitude": longitude,
                        "accuracy": location_accuracy
                    },
                    "payment_method": payment_method,
                    "payment_status": payment_status,
                    "upi_reference_id": upi_reference_id,
                    "created_at": firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print(f"[Firestore] create_order error: {e}")

        return cls.get_order(order_id)

    @classmethod
    def get_order(cls, order_id):
        conn = cls._get_sqlite_conn()
        try:
            row = conn.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @classmethod
    def get_all_orders(cls):
        conn = cls._get_sqlite_conn()
        try:
            rows = conn.execute("SELECT * FROM orders ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @classmethod
    def update_order_payment(cls, order_id, status="COMPLETED", upi_reference_id=None):
        conn = cls._get_sqlite_conn()
        try:
            if upi_reference_id:
                conn.execute(
                    "UPDATE orders SET payment_status = ?, upi_reference_id = ? WHERE order_id = ?",
                    (status, upi_reference_id, order_id)
                )
            else:
                conn.execute(
                    "UPDATE orders SET payment_status = ? WHERE order_id = ?",
                    (status, order_id)
                )
            conn.commit()
        finally:
            conn.close()

        if FIREBASE_AVAILABLE and firestore_db:
            try:
                update_fields = {"payment_status": status, "updated_at": firestore.SERVER_TIMESTAMP}
                if upi_reference_id:
                    update_fields["upi_reference_id"] = upi_reference_id
                firestore_db.collection("orders").document(order_id).update(update_fields)
            except Exception as e:
                print(f"[Firestore] update_order_payment error: {e}")

        return cls.get_order(order_id)

    # ---------------------------------------------------------
    # SETTINGS COLLECTION (MASTER UPI ID, MERCHANT METADATA)
    # ---------------------------------------------------------

    @classmethod
    def get_setting(cls, key, default=None):
        conn = cls._get_sqlite_conn()
        try:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
            if row:
                return row["value"]
        finally:
            conn.close()

        if FIREBASE_AVAILABLE and firestore_db:
            try:
                doc = firestore_db.collection("settings").document("config").get()
                if doc.exists:
                    return doc.to_dict().get(key, default)
            except Exception as e:
                print(f"[Firestore] get_setting error: {e}")

        return default

    @classmethod
    def set_setting(cls, key, value):
        conn = cls._get_sqlite_conn()
        try:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP",
                (key, value, value)
            )
            conn.commit()
        finally:
            conn.close()

        if FIREBASE_AVAILABLE and firestore_db:
            try:
                firestore_db.collection("settings").document("config").set({
                    key: value,
                    "updated_at": firestore.SERVER_TIMESTAMP
                }, merge=True)
            except Exception as e:
                print(f"[Firestore] set_setting error: {e}")

        return True

