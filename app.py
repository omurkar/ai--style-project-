from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
    jsonify
)

from pathlib import Path
from werkzeug.utils import secure_filename
import os

# Load .env variables (GEMINI_API_KEY etc.) before anything else
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass
import uuid
import time
from datetime import timedelta
import cv2
from functools import wraps

from database import get_connection, initialize_database
from security.auth import hash_password, verify_password

# =========================================================
# FIREBASE & NEW SERVICES
# =========================================================

from firebase_service import (
    FirestoreRepository,
    verify_google_id_token,
    upload_clothing_asset,
    FIREBASE_AVAILABLE
)

from local_storage_db import LocalClothingAssetDB

from payment_service import (
    get_master_upi_id,
    get_merchant_name,
    update_master_upi_config,
    generate_order_upi_qr
)


# =========================================================
# OPTIONAL AI MODULE
# =========================================================

try:
    from body_analysis import analyze_body

    BODY_ANALYSIS_AVAILABLE = True

except Exception as error:

    analyze_body = None
    BODY_ANALYSIS_AVAILABLE = False

    print(
        "Body analysis module could not be loaded:",
        error
    )


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "ai-style-development-secret-key"
)

app.permanent_session_lifetime = timedelta(days=30)


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

STORAGE_DIR = BASE_DIR / "storage"

TEMP_PHOTO_DIR = (
    STORAGE_DIR / "temp"
)

CLOTHING_DIR = (
    STORAGE_DIR / "clothing"
)

VTON_RESULT_DIR = (
    STORAGE_DIR
    / "temp"
    / "vton_results"
)

TEMP_PHOTO_DIR.mkdir(
    parents=True,
    exist_ok=True
)

CLOTHING_DIR.mkdir(
    parents=True,
    exist_ok=True
)

VTON_RESULT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# FILE SETTINGS
# =========================================================

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp"
}

MAX_FILE_SIZE = 10 * 1024 * 1024


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

initialize_database()


# =========================================================
# FIREBASE CLIENT CONFIGURATION (passed to templates)
# =========================================================

FIREBASE_CLIENT_CONFIG = {
    "firebase_api_key": os.getenv("FIREBASE_API_KEY", "AIzaSyC5cp0005FR4MnSRpgzzLLo-cu-jcSKWXU"),
    "firebase_auth_domain": os.getenv("FIREBASE_AUTH_DOMAIN", "sandya-project.firebaseapp.com"),
    "firebase_project_id": os.getenv("FIREBASE_PROJECT_ID", "sandya-project"),
    "firebase_storage_bucket": os.getenv("FIREBASE_STORAGE_BUCKET", "sandya-project.firebasestorage.app"),
    "firebase_messaging_sender_id": os.getenv("FIREBASE_MESSAGING_SENDER_ID", "889198140804"),
    "firebase_app_id": os.getenv("FIREBASE_APP_ID", "1:889198140804:web:2bd6a89e4aaae33bbdd1d1"),
    "firebase_measurement_id": os.getenv("FIREBASE_MEASUREMENT_ID", "G-GNPBJCFEJE"),
}


# =========================================================
# ROUTE GUARDS / DECORATORS
# =========================================================

def login_required(f):
    """Redirect to login if user is not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Restrict route to admin-role users only."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "error")
            return redirect(url_for("login"))
        conn = get_connection()
        try:
            user = conn.execute(
                "SELECT role FROM users WHERE id = ?",
                (session["user_id"],)
            ).fetchone()
        finally:
            conn.close()
        if not user or user["role"] != "admin":
            flash("Access denied. Admin privileges required.", "error")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def allowed_file(filename):

    if not filename:
        return False

    if "." not in filename:
        return False

    extension = (
        filename
        .rsplit(".", 1)[1]
        .lower()
    )

    return extension in ALLOWED_EXTENSIONS


def convert_height_to_cm(
    height_value,
    height_unit
):

    """
    Convert manually entered height
    into centimetres.

    Supported:
    - cm
    - ft
    - in
    """

    try:

        value = float(
            height_value
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    if value <= 0:
        return None

    if height_unit == "cm":

        return value

    if height_unit == "in":

        return value * 2.54

    if height_unit == "ft":

        return value * 30.48

    return None


def validate_image_file(
    file_path
):

    """
    Basic server-side
    image validation.
    """

    try:

        image = cv2.imread(
            str(file_path)
        )

        if image is None:
            return False

        if (
            image.shape[0] < 100
            or image.shape[1] < 100
        ):

            return False

        return True

    except Exception:

        return False


def normalize_analysis_result(
    result
):

    """
    Convert body_analysis.py
    output into safe application values.
    """

    if not isinstance(
        result,
        dict
    ):

        return {

            "success": False,

            "body_shape":
                "Not Determined",

            "body_proportions":
                "Not Determined",

            "leg_proportion":
                "Not Determined",

            "shoulder_width_ratio":
                None,

            "hip_width_ratio":
                None,

            "message":
                "Invalid analysis result."

        }

    return {

        "success":
            bool(
                result.get(
                    "success",
                    False
                )
            ),

        "body_shape":
            result.get(
                "body_shape",
                "Not Determined"
            ),

        "body_proportions":
            result.get(
                "body_proportions",
                "Not Determined"
            ),

        "leg_proportion":
            result.get(
                "leg_proportion",
                "Not Determined"
            ),

        "shoulder_width_ratio":
            result.get(
                "shoulder_width_ratio"
            ),

        "hip_width_ratio":
            result.get(
                "hip_width_ratio"
            ),

        "message":
            result.get(
                "message",
                ""
            )
    }


# =========================================================
# RUN BODY ANALYSIS
# =========================================================

def run_body_analysis(
    photo_path
):

    """
    Run MediaPipe body analysis
    on the newly uploaded photograph.

    IMPORTANT:
    body_analysis.py currently accepts
    only the photo path.
    """

    if not BODY_ANALYSIS_AVAILABLE:

        return {

            "success": False,

            "body_shape":
                "Not Determined",

            "body_proportions":
                "Not Determined",

            "leg_proportion":
                "Not Determined",

            "shoulder_width_ratio":
                None,

            "hip_width_ratio":
                None,

            "message":
                "Body analysis module is not available."

        }


    try:

        print(
            "Running MediaPipe analysis..."
        )

        print(
            f"Image used: {photo_path}"
        )

        # IMPORTANT:
        # Do NOT pass category here.
        # analyze_body() accepts one argument.
        result = analyze_body(
            str(photo_path)
        )

        normalized_result = (
            normalize_analysis_result(
                result
            )
        )

        print(
            "Normalized body analysis:"
        )

        print(
            normalized_result
        )

        return normalized_result


    except Exception as error:

        print("=" * 60)

        print(
            "BODY ANALYSIS ERROR"
        )

        print(error)

        print("=" * 60)

        return {

            "success": False,

            "body_shape":
                "Not Determined",

            "body_proportions":
                "Not Determined",

            "leg_proportion":
                "Not Determined",

            "shoulder_width_ratio":
                None,

            "hip_width_ratio":
                None,

            "message":
                "Body analysis could not be completed."

        }


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user():

    if "user_id" not in session:

        return None

    connection = get_connection()

    try:

        user = connection.execute(
            """
            SELECT *
            FROM users
            WHERE id = ?
            """,
            (
                session["user_id"],
            )
        ).fetchone()

        return dict(user) if user else None

    finally:

        connection.close()


# =========================================================
# HOME & SEARCH FILTERING (TAG-BASED)
# =========================================================

def filter_clothing_by_tags(items, query):
    """
    Tag-based clothing search filtering.
    Dynamically generates tags from item metadata (category, occasion, style,
    clothing_type, colour, brand, outfit_name, description) including natural
    language tag variants (e.g. 'women clothes', 'party clothes', 'casual clothes').
    """
    if not query:
        return items

    q = query.strip().lower()
    q_tokens = [tok for tok in q.split() if tok]
    if not q_tokens:
        return items

    results = []
    for item in items:
        cat = (item.get("category") or "").strip().lower()
        occ = (item.get("occasion") or "").strip().lower()
        sty = (item.get("style") or "").strip().lower()
        ctype = (item.get("clothing_type") or "").strip().lower()
        col = (item.get("colour") or "").strip().lower()
        brand = (item.get("brand") or "").strip().lower()
        name = (item.get("outfit_name") or "").strip().lower()
        desc = (item.get("description") or "").strip().lower()

        tags = set()
        if cat:
            tags.add(cat)
            tags.add(f"{cat} clothes")
            tags.add(f"{cat} wear")
            tags.add(f"{cat}'s clothes")
            tags.add(f"{cat} clothing")
        if occ:
            tags.add(occ)
            tags.add(f"{occ} clothes")
            tags.add(f"{occ} wear")
            tags.add(f"{occ} outfits")
            tags.add(f"{occ} clothing")
            if occ.endswith("s"):
                tags.add(occ.rstrip("s"))
                tags.add(f"{occ.rstrip('s')} clothes")
            else:
                tags.add(f"{occ}s")
                tags.add(f"{occ}s clothes")
            if "party" in occ:
                tags.add("parties")
                tags.add("party clothes")
                tags.add("parties clothes")
            if "formal" in occ:
                tags.add("formals")
                tags.add("formal clothes")
                tags.add("formals clothes")
        if sty:
            tags.add(sty)
            tags.add(f"{sty} clothes")
            tags.add(f"{sty} wear")
            tags.add(f"{sty} style")
            if "party" in sty:
                tags.add("parties")
                tags.add("party clothes")
            if "formal" in sty:
                tags.add("formals")
                tags.add("formal clothes")
        if ctype:
            tags.add(ctype)
            tags.add(f"{ctype}s")
            tags.add(f"{ctype} clothes")
        if col:
            tags.add(col)
        if brand:
            tags.add(brand)

        searchable_text = f"{name} {desc} {' '.join(tags)}".lower()

        # 1. Exact phrase / substring match in searchable text or tags
        if q in searchable_text or any(q in t or t in q for t in tags):
            results.append(item)
            continue

        # 2. All query tokens present in searchable text or tags
        if all(token in searchable_text for token in q_tokens):
            results.append(item)
            continue

        # 3. Any token matches a primary attribute
        primary_attributes = {cat, occ, sty, ctype, col, brand}
        if any(tok in primary_attributes for tok in q_tokens):
            results.append(item)
            continue

    return results


@app.route("/")
def home():
    q = request.args.get("q", "").strip()
    all_products = LocalClothingAssetDB.get_all_local_clothing()
    if q:
        filtered_products = filter_clothing_by_tags(all_products, q)
    else:
        filtered_products = all_products

    return render_template(
        "index.html",
        products=filtered_products,
        search_query=q
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        full_name = request.form.get(
            "full_name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        category = request.form.get(
            "category",
            ""
        ).strip()

        age_value = request.form.get(
            "age",
            ""
        ).strip()


        if (
            not full_name
            or not email
            or not password
        ):

            flash(
                "Please fill all required fields.",
                "error"
            )

            return render_template(
                "register.html",
                **FIREBASE_CLIENT_CONFIG
            )


        if password != confirm_password:

            flash(
                "Passwords do not match. Please verify and try again.",
                "error"
            )

            return render_template(
                "register.html",
                **FIREBASE_CLIENT_CONFIG
            )


        try:

            age = (
                int(age_value)
                if age_value
                else None
            )

        except ValueError:

            age = None


        password_hash = (
            hash_password(password)
        )


        connection = get_connection()

        try:

            existing_user = connection.execute(
                """
                SELECT id
                FROM users
                WHERE email = ?
                """,
                (
                    email,
                )
            ).fetchone()


            if existing_user:

                flash(
                    "An account with this email already exists.",
                    "error"
                )

                return render_template(
                    "register.html",
                    **FIREBASE_CLIENT_CONFIG
                )


            cursor = connection.execute(
                """
                INSERT INTO users
                (
                    full_name,
                    email,
                    password_hash,
                    category,
                    age
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    full_name,
                    email,
                    password_hash,
                    category or None,
                    age
                )
            )

            connection.commit()

            user_id = cursor.lastrowid


            connection.execute(
                """
                INSERT OR IGNORE INTO style_profiles
                (
                    user_id,
                    analysis_status
                )
                VALUES (?, ?)
                """,
                (
                    user_id,
                    "pending"
                )
            )

            connection.commit()

        finally:

            connection.close()


        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html",
        **FIREBASE_CLIENT_CONFIG
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        connection = get_connection()

        try:

            user = connection.execute(
                """
                SELECT *
                FROM users
                WHERE email = ?
                """,
                (
                    email,
                )
            ).fetchone()

        finally:

            connection.close()


        if (
            user
            and verify_password(
                password,
                user["password_hash"]
            )
        ):

            user_dict = dict(user)

            session.clear()

            session.permanent = True

            session["user_id"] = (
                user_dict["id"]
            )

            session["user_email"] = (
                user_dict["email"]
            )

            session["user_name"] = (
                user_dict["full_name"]
            )

            # Store role in session safely
            role = user_dict.get("role") or "user"
            session["user_role"] = role

            flash(
                "Login successful.",
                "success"
            )

            if role == "admin":
                return redirect(
                    url_for("admin_dashboard")
                )

            # Redirect regular user directly to the Homepage (Catalog)
            return redirect(
                url_for("home")
            )


        flash(
            "Invalid email or password.",
            "error"
        )


    return render_template(
        "login.html",
        **FIREBASE_CLIENT_CONFIG
    )
# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("login")
    )


# =========================================================
# PROFILE
# =========================================================

@app.route("/profile")
def profile():

    user = get_current_user()


    if user is None:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    connection = get_connection()

    try:

        profile_row = connection.execute(
            """
            SELECT *
            FROM style_profiles
            WHERE user_id = ?
            """,
            (
                session["user_id"],
            )
        ).fetchone()

    finally:

        connection.close()


    return render_template(
        "profile.html",
        user=user,
        profile=profile_row
    )


# =========================================================
# UPDATE FASHION PREFERENCES
# =========================================================

@app.route("/profile/preferences", methods=["POST"])
def update_preferences():
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    preferred_style = request.form.get("preferred_style", "").strip()
    preferred_occasion = request.form.get("preferred_occasion", "").strip()
    budget_raw = request.form.get("budget", "").strip()

    budget_val = None
    if budget_raw:
        # Extract numerical value e.g. "Under ₹1,000" -> 1000.0, "1500" -> 1500.0
        clean_num = "".join(c for c in budget_raw if c.isdigit() or c == ".")
        try:
            budget_val = float(clean_num) if clean_num else None
        except ValueError:
            budget_val = None

    connection = get_connection()
    try:
        connection.execute(
            """
            UPDATE style_profiles
            SET preferred_style = ?,
                preferred_occasion = ?,
                budget = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                preferred_style or None,
                preferred_occasion or None,
                budget_val,
                session["user_id"]
            )
        )
        connection.commit()
        flash("Fashion preferences updated successfully.", "success")
    finally:
        connection.close()

    return redirect(url_for("profile"))


# =========================================================
# UPLOAD PAGE
# =========================================================

@app.route("/upload")
def upload():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    return render_template(
        "upload.html"
    )


# =========================================================
# UPLOAD PHOTO + RUN AI ANALYSIS
# =========================================================

@app.route(
    "/upload-photo",
    methods=["POST"]
)
def upload_photo():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    photo = request.files.get(
        "photo"
    )

    saved_face_path = get_uploaded_photo_path()

    if (photo is None or not photo.filename) and saved_face_path and saved_face_path.exists():
        photo_path = saved_face_path
    elif photo is None or not photo.filename:
        flash(
            "Please select or capture a photo.",
            "error"
        )
        return redirect(
            url_for("upload")
        )
    else:
        if not allowed_file(photo.filename):
            flash(
                "Only JPG, JPEG, PNG and WEBP images are allowed.",
                "error"
            )
            return redirect(url_for("upload"))

        # File size check
        photo.stream.seek(0, os.SEEK_END)
        file_size = photo.stream.tell()
        photo.stream.seek(0)

        if file_size > MAX_FILE_SIZE:
            flash("Photo must be smaller than 10 MB.", "error")
            return redirect(url_for("upload"))

        extension = photo.filename.rsplit(".", 1)[1].lower()
        unique_name = f"user_{session['user_id']}_{uuid.uuid4().hex}.{extension}"
        safe_name = secure_filename(unique_name)
        photo_path = TEMP_PHOTO_DIR / safe_name
        photo.save(photo_path)

        if not validate_image_file(photo_path):
            try:
                photo_path.unlink()
            except Exception:
                pass
            flash("The uploaded file is not a valid image.", "error")
            return redirect(url_for("upload"))


    # -----------------------------------------------------
    # MANUAL HEIGHT
    # -----------------------------------------------------

    height_value = request.form.get(
        "height",
        ""
    ).strip()


    height_unit = request.form.get(
        "height_unit",
        "cm"
    ).strip()


    height_cm = (
        convert_height_to_cm(
            height_value,
            height_unit
        )
    )


    if height_cm is None:

        try:

            photo_path.unlink()

        except Exception:

            pass


        flash(
            "Please enter a valid height.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


    # -----------------------------------------------------
    # REMOVE OLD BODY ANALYSIS SESSION
    # -----------------------------------------------------

    session.pop(
        "body_analysis",
        None
    )


    # -----------------------------------------------------
    # RUN FRESH AI BODY ANALYSIS
    # -----------------------------------------------------

    print("=" * 60)

    print(
        "RUNNING FRESH AI BODY ANALYSIS"
    )

    print("=" * 60)

    print(
        f"New photo: {photo_path}"
    )

    print(
        f"Manual height: {height_cm:.1f} cm"
    )


    analysis_result = (
        run_body_analysis(
            photo_path
        )
    )


    print(
        "Final analysis result:"
    )

    print(
        analysis_result
    )

    print("=" * 60)


    # -----------------------------------------------------
    # STORE CURRENT PHOTO IN SESSION
    # -----------------------------------------------------

    session["uploaded_photo"] = str(
        photo_path.relative_to(
            BASE_DIR
        )
    )

    # Compatibility with the older VTON session key.
    session["photo_path"] = str(photo_path)

    session["height_cm"] = round(
        height_cm,
        1
    )


    session["body_analysis"] = (
        analysis_result
    )


    return redirect(
        url_for("analysis")
    )



# =========================================================
# RESOLVE CURRENT USER PHOTO & FACE TEMPLATE
# =========================================================

def get_uploaded_photo_path():
    """Resolve the current user's uploaded photo or face template reliably."""

    candidates = []

    # 1. Prioritize active face template
    face_template_relative = session.get("face_template")
    if face_template_relative:
        candidates.append(BASE_DIR / str(face_template_relative))

    uploaded_relative = session.get("uploaded_photo")
    if uploaded_relative:
        candidates.append(BASE_DIR / str(uploaded_relative))

    legacy_path = session.get("photo_path")
    if legacy_path:
        legacy = Path(str(legacy_path))
        candidates.append(
            legacy if legacy.is_absolute() else BASE_DIR / legacy
        )

    user_id = session.get("user_id")
    if user_id:
        from firebase_service import FirestoreRepository
        db_tmpl = FirestoreRepository.get_user_face_template(user_id)
        if db_tmpl:
            candidates.append(BASE_DIR / str(db_tmpl))

        # Check storage/users/ directory
        user_storage_tmpl = BASE_DIR / "storage" / "users" / f"user_{user_id}_face_template.png"
        candidates.append(user_storage_tmpl)

    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_file():
                return candidate
        except Exception:
            pass

    if user_id:
        temp_dir = BASE_DIR / "storage" / "temp"
        if temp_dir.exists():
            matching = [
                p for p in temp_dir.iterdir()
                if p.is_file()
                and p.name.lower().startswith(f"user_{user_id}_")
            ]
            if matching:
                matching.sort(
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                return matching[0]

    return None


# =========================================================
# USER PHOTO & FACE TEMPLATE ROUTES
# =========================================================

@app.route("/user-photo")
def user_photo():

    if "user_id" not in session:
        return "", 401

    photo_path = get_uploaded_photo_path()

    if photo_path is None:
        return "", 404

    try:
        session["uploaded_photo"] = str(
            photo_path.relative_to(BASE_DIR)
        )
        session["photo_path"] = str(photo_path)
    except ValueError:
        pass

    return send_file(photo_path)


@app.route("/user-face-template")
def user_face_template():
    """Serve the active oval-cropped face template."""
    if "user_id" not in session:
        return "", 401

    photo_path = get_uploaded_photo_path()
    if photo_path is None or not photo_path.exists():
        return "", 404

    return send_file(photo_path)


@app.route("/detect-face-bounds", methods=["POST"])
def detect_face_bounds():
    """
    Detect frontal face coordinates in an uploaded base64 image
    to provide 1-click automatic oval framing.
    """
    import base64
    import io
    from PIL import Image
    import cv2
    import numpy as np

    data = request.get_json(silent=True) or {}
    raw_data = data.get("image_data", "")
    if not raw_data:
        return jsonify({"success": False, "error": "No image data provided"}), 400

    if "," in raw_data:
        raw_data = raw_data.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(raw_data)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img_w, img_h = pil_img.size

        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=3)

        if len(faces) == 0:
            # Fallback to profile face detector
            prof_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
            faces = prof_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=3)

        if len(faces) > 0:
            # Pick largest detected face
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            return jsonify({
                "success": True,
                "face": {
                    "x": int(fx),
                    "y": int(fy),
                    "width": int(fw),
                    "height": int(fh),
                    "img_width": int(img_w),
                    "img_height": int(img_h)
                }
            })

        return jsonify({"success": False, "message": "No face detected"})
    except Exception as err:
        return jsonify({"success": False, "error": str(err)}), 500


@app.route("/save-face-template", methods=["POST"])
def save_face_template():
    """
    Validates and stores the user's oval-cropped face template.
    Enforces that a face is present, softens boundaries, and saves
    to both session and database for all future virtual try-ons.
    """
    import base64
    import io
    from PIL import Image
    import cv2
    import numpy as np

    if "user_id" not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401

    data = request.get_json(silent=True) or {}
    raw_data = data.get("image_data", "")
    if not raw_data:
        return jsonify({"success": False, "error": "No image data provided"}), 400

    if "," in raw_data:
        raw_data = raw_data.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(raw_data)
        pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        w, h = pil_img.size

        # Verify face presence using OpenCV
        np_img = np.array(pil_img)
        bgr = cv2.cvtColor(np_img[:, :, :3], cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.06, minNeighbors=2)

        # Eye cascade verification as secondary check
        eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
        eyes = eye_cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=2)

        # Skin color proportion in HSV space
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
        lower_skin = np.array([0, 15, 40], dtype=np.uint8)
        upper_skin = np.array([30, 200, 255], dtype=np.uint8)
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        skin_ratio = np.count_nonzero(skin_mask) / float(w * h)

        is_valid_face = (len(faces) > 0) or (len(eyes) >= 1) or (skin_ratio > 0.20)

        if not is_valid_face:
            return jsonify({
                "success": False,
                "error": "Only photos containing a clear face can be used. Please ensure your face is framed within the oval."
            }), 400

        # Save template to storage/users/ and storage/temp/
        users_dir = BASE_DIR / "storage" / "users"
        users_dir.mkdir(parents=True, exist_ok=True)
        template_file = users_dir / f"user_{session['user_id']}_face_template.png"

        temp_dir = BASE_DIR / "storage" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"user_{session['user_id']}_face_template.png"

        pil_img.save(str(template_file), "PNG")
        pil_img.save(str(temp_file), "PNG")

        relative_path = f"storage/users/{template_file.name}"

        # Update session
        session["face_template"] = relative_path
        session["uploaded_photo"] = relative_path
        session["photo_path"] = str(template_file)

        # Update database persistence
        from firebase_service import FirestoreRepository
        FirestoreRepository.update_user_face_template(session["user_id"], relative_path)

        return jsonify({
            "success": True,
            "message": "Face template successfully saved and ready for virtual try-on!",
            "template_url": f"/user-face-template?t={int(time.time())}"
        })
    except Exception as err:
        return jsonify({"success": False, "error": f"Failed to process face template: {err}"}), 500


# =========================================================
# LOCAL STORAGE ASSET ROUTE
# Serves clothing images and assets from storage/ directory
# =========================================================

@app.route("/storage/<path:filename>")
def serve_storage_file(filename):
    from flask import send_from_directory
    return send_from_directory(STORAGE_DIR, filename)



# =========================================================
# ANALYSIS PAGE
# =========================================================

@app.route("/analysis")
def analysis():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    analysis_result = session.get(
        "body_analysis",
        {}
    )


    height_cm = session.get(
        "height_cm"
    )


    user = get_current_user()


    if user is None:

        return redirect(
            url_for("login")
        )


    category = (
        user["category"]
        or "Women"
    )


    # -----------------------------------------------------
    # CURRENT AI BODY RESULTS
    # -----------------------------------------------------

    detected_body_shape = (
        analysis_result.get(
            "body_shape",
            "Not Determined"
        )
    )


    detected_body_proportions = (
        analysis_result.get(
            "body_proportions",
            "Not Determined"
        )
    )


    leg_proportion = (
        analysis_result.get(
            "leg_proportion",
            "Not Determined"
        )
    )


    # -----------------------------------------------------
    # GET EXISTING STYLE PROFILE
    # -----------------------------------------------------

    connection = get_connection()

    try:

        profile_row = connection.execute(
            """
            SELECT *
            FROM style_profiles
            WHERE user_id = ?
            """,
            (
                session["user_id"],
            )
        ).fetchone()

    finally:

        connection.close()


    profile = (
        dict(profile_row)
        if profile_row
        else {}
    )


    # -----------------------------------------------------
    # SKIN TONE / UNDERTONE
    #
    # These are currently profile/demo values.
    # Actual skin-tone AI will be implemented separately.
    # -----------------------------------------------------

    skin_tone = (
        profile.get("skin_tone")
        or session.get(
            "detected_skin_tone",
            "Medium"
        )
    )


    undertone = (
        profile.get("undertone")
        or session.get(
            "detected_undertone",
            "Warm"
        )
    )


    # -----------------------------------------------------
    # KIDS
    # -----------------------------------------------------

    if category == "Kids":

        detected_body_shape = (
            "Not Applicable"
        )

        detected_body_proportions = (
            "Not Applicable"
        )


    return render_template(
        "analysis.html",

        category=category,

        skin_tone=skin_tone,

        undertone=undertone,

        body_shape=
            detected_body_shape,

        body_proportions=
            detected_body_proportions,

        leg_proportion=
            leg_proportion,

        height_cm=height_cm,

        analysis_result=
            analysis_result
    )


# =========================================================
# SAVE ANALYSIS
# =========================================================

@app.route(
    "/save-analysis",
    methods=["POST"]
)
def save_analysis():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    category = request.form.get(
        "category",
        "Women"
    ).strip()


    skin_tone = request.form.get(
        "skin_tone",
        "Medium"
    ).strip()


    undertone = request.form.get(
        "undertone",
        "Warm"
    ).strip()


    body_shape = request.form.get(
        "body_shape",
        "Not Determined"
    ).strip()


    body_proportions = request.form.get(
        "body_proportions",
        "Not Determined"
    ).strip()


    height_cm = session.get(
        "height_cm"
    )


    if category == "Kids":

        body_shape = (
            "Not Applicable"
        )

        body_proportions = (
            "Not Applicable"
        )


    connection = get_connection()

    try:

        connection.execute(
            """
            INSERT INTO style_profiles
            (
                user_id,
                skin_tone,
                undertone,
                body_shape,
                body_proportions,
                height_cm,
                analysis_status,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)

            ON CONFLICT(user_id)
            DO UPDATE SET

                skin_tone =
                    excluded.skin_tone,

                undertone =
                    excluded.undertone,

                body_shape =
                    excluded.body_shape,

                body_proportions =
                    excluded.body_proportions,

                height_cm =
                    excluded.height_cm,

                analysis_status =
                    excluded.analysis_status,

                updated_at =
                    CURRENT_TIMESTAMP
            """,

            (
                session["user_id"],
                skin_tone,
                undertone,
                body_shape,
                body_proportions,
                height_cm,
                "completed"
            )
        )


        connection.execute(
            """
            UPDATE users
            SET category = ?
            WHERE id = ?
            """,

            (
                category,
                session["user_id"]
            )
        )


        connection.commit()


    finally:

        connection.close()


    # Keep uploaded_photo and
    # height available for VTON.
    session.pop(
        "body_analysis",
        None
    )


    flash(
        "AI style analysis saved successfully.",
        "success"
    )


    return redirect(
        url_for("recommendations")
    )


# =========================================================
# RECOMMENDATIONS
# =========================================================

@app.route("/recommendations")
def recommendations():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    from recommendation_engine import (
        get_recommendations
    )


    occasion = request.args.get(
        "occasion",
        "All Occasions"
    ).strip()


    style = request.args.get(
        "style",
        "All Styles"
    ).strip()


    budget = request.args.get(
        "budget",
        "Any Budget"
    ).strip()


    connection = get_connection()

    try:

        profile_row = connection.execute(
            """
            SELECT
                u.category,
                sp.skin_tone,
                sp.undertone,
                sp.body_shape,
                sp.body_proportions,
                sp.height_cm,
                sp.preferred_style,
                sp.preferred_occasion,
                sp.budget
            FROM users u
            LEFT JOIN style_profiles sp
                ON sp.user_id = u.id

            WHERE u.id = ?
            """,

            (
                session["user_id"],
            )
        ).fetchone()


        clothing_rows = connection.execute(
            """
            SELECT *
            FROM clothing
            ORDER BY id ASC
            """
        ).fetchall()


    finally:

        connection.close()


    if profile_row is None:

        flash(
            "Please complete your style profile first.",
            "error"
        )

        return redirect(
            url_for("profile")
        )


    profile = dict(
        profile_row
    )


    clothing = [
        dict(row)
        for row in clothing_rows
    ]


    if not profile.get(
        "category"
    ):

        flash(
            "Please complete your style analysis first.",
            "error"
        )

        return redirect(
            url_for("analysis")
        )


    recommendations_list = (
        get_recommendations(

            profile=profile,

            clothing_rows=clothing,

            occasion=occasion,

            style=style,

            budget=budget,

            limit=6
        )
    )


    return render_template(

        "recommendations.html",

        profile=profile,

        recommendations=
            recommendations_list,

        occasion=occasion,

        style=style,

        budget=budget
    )


# =========================================================
# OUTFIT DETAILS
# =========================================================

@app.route("/outfit")
def outfit():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    outfit_id = request.args.get(
        "outfit_id",
        ""
    ).strip()


    if not outfit_id:

        flash(
            "Please select an outfit first.",
            "error"
        )

        return redirect(
            url_for("recommendations")
        )


    connection = get_connection()

    try:

        outfit_row = connection.execute(
            """
            SELECT *
            FROM clothing
            WHERE outfit_id = ?
            """,
            (
                outfit_id,
            )
        ).fetchone()

    finally:

        connection.close()


    if outfit_row is None:

        flash(
            "The selected outfit was not found.",
            "error"
        )

        return redirect(
            url_for("recommendations")
        )


    outfit_data = dict(
        outfit_row
    )


    return render_template(
        "outfit.html",
        outfit=outfit_data
    )


# =========================================================
# VIRTUAL TRY-ON PAGE
# =========================================================

@app.route("/tryon")
def tryon():

    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("login"))

    clothing_id = request.args.get("clothing_id", "").strip()

    if not clothing_id:
        flash("Please select an outfit first.", "error")
        return redirect(url_for("recommendations"))

    connection = get_connection()
    try:
        outfit_row = connection.execute(
            """
            SELECT *
            FROM clothing
            WHERE id = ?
            """,
            (clothing_id,)
        ).fetchone()
    finally:
        connection.close()

    if outfit_row is None:
        flash("Selected outfit was not found.", "error")
        return redirect(url_for("recommendations"))

    outfit = dict(outfit_row)

    # Resolve the real uploaded photo from the current session.
    photo_path = get_uploaded_photo_path()
    photo_exists = (
        photo_path is not None
        and photo_path.exists()
        and photo_path.is_file()
    )

    if photo_exists:
        try:
            relative_photo = str(photo_path.relative_to(BASE_DIR))
            session["uploaded_photo"] = relative_photo
            session["photo_path"] = str(photo_path)
        except ValueError:
            pass

    print(
        "TRY-ON PHOTO:",
        photo_path if photo_path else "NOT FOUND"
    )

    # Pass BOTH variable names because the template versions
    # used in this project have used both.
    return render_template(
        "tryon.html",
        outfit=outfit,
        photo_exists=photo_exists,
        photo_available=photo_exists,
        clothing_image_url=(
            "/" + outfit["image_path"]
            if outfit.get("image_path")
            else None
        )
    )


# =========================================================
# GENERATE VIRTUAL TRY-ON
# =========================================================

@app.route(
    "/generate-tryon",
    methods=["POST"]
)
def generate_tryon():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    clothing_id = request.form.get(
        "clothing_id",
        ""
    ).strip()


    if not clothing_id:

        flash(
            "No outfit was selected.",
            "error"
        )

        return redirect(
            url_for("recommendations")
        )


    person_image = get_uploaded_photo_path()

    if person_image is None:

        flash(
            "Please upload your photo first.",
            "error"
        )

        return redirect(
            url_for("upload")
        )

    try:
        photo_relative = str(
            person_image.relative_to(BASE_DIR)
        )
    except ValueError:
        photo_relative = str(person_image)


    connection = get_connection()

    try:

        outfit_row = connection.execute(
            """
            SELECT *
            FROM clothing
            WHERE id = ?
            """,
            (
                clothing_id,
            )
        ).fetchone()

    finally:

        connection.close()


    if outfit_row is None:

        flash(
            "Selected outfit was not found.",
            "error"
        )

        return redirect(
            url_for("recommendations")
        )


    outfit = dict(
        outfit_row
    )


    tryon_image_path = (
        outfit.get(
            "tryon_image_path"
        )
        # Fallback: use the regular clothing image_path if no dedicated tryon image
        or outfit.get("image_path")
    )


    if not tryon_image_path:

        flash(
            "This outfit does not have a garment image configured for try-on.",
            "error"
        )

        return redirect(
            url_for(
                "outfit",
                outfit_id=
                    outfit["outfit_id"]
            )
        )


    garment_image = (
        BASE_DIR
        / tryon_image_path
    )


    if not garment_image.exists():

        flash(
            "The garment image for this outfit could not be found on the server.",
            "error"
        )

        return redirect(
            url_for(
                "outfit",
                outfit_id=
                    outfit["outfit_id"]
            )
        )


    try:

        from vton_service import (
            generate_virtual_tryon
        )


        print("=" * 40)

        print(
            "STARTING VIRTUAL TRY-ON"
        )

        print("=" * 40)


        result_file, mask_file = (
            generate_virtual_tryon(

                person_image=
                    person_image,

                garment_image=
                    garment_image,

                garment_description=(
                    outfit.get(
                        "outfit_name"
                    )
                    or "clothing item"
                ),

                face_target=outfit.get("face_target")
            )
        )


        # -------------------------------------------------
        # SAVE DATABASE RECORD
        # -------------------------------------------------

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO tryon_results
                (
                    user_id,
                    clothing_id,
                    original_photo_path,
                    result_photo_path
                )
                VALUES (?, ?, ?, ?)
                """,

                (
                    session["user_id"],

                    outfit["id"],

                    str(
                        photo_relative
                    ),

                    str(
                        result_file.relative_to(
                            BASE_DIR
                        )
                    )
                )
            )

            connection.commit()

        finally:

            connection.close()


        session["tryon_result"] = str(
            result_file.relative_to(
                BASE_DIR
            )
        )


        session["tryon_outfit_id"] = (
            outfit["outfit_id"]
        )


        flash(
            "Virtual try-on generated successfully.",
            "success"
        )


        return redirect(
            url_for(
                "tryon_result"
            )
        )


    except Exception as error:

        print("=" * 40)
        print("VIRTUAL TRY-ON PRIMARY ERROR, ATTEMPTING DIRECT FALLBACK:")
        print(error)
        print("=" * 40)

        try:
            from vton_service import place_user_face_on_clothing
            print("[Direct Overlay] Generating face placement try-on...")
            result_file, mask_file = place_user_face_on_clothing(
                person_image=person_image,
                garment_image=garment_image,
                face_target=outfit.get("face_target")
            )

            connection = get_connection()
            try:
                connection.execute(
                    """
                    INSERT INTO tryon_results
                    (user_id, clothing_id, original_photo_path, result_photo_path)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        session["user_id"],
                        outfit["id"],
                        str(photo_relative),
                        str(result_file.relative_to(BASE_DIR))
                    )
                )
                connection.commit()
            finally:
                connection.close()

            session["tryon_result"] = str(result_file.relative_to(BASE_DIR))
            session["tryon_outfit_id"] = outfit["outfit_id"]

            flash("Virtual try-on generated successfully.", "success")
            return redirect(url_for("tryon_result"))

        except Exception as fallback_err:
            print("=" * 40)
            print("CRITICAL TRY-ON FALLBACK ERROR:")
            print(fallback_err)
            print("=" * 40)

            flash(
                f"Virtual try-on could not be generated: {fallback_err}",
                "error"
            )

            return redirect(
                url_for(
                    "outfit",
                    outfit_id=outfit["outfit_id"]
                )
            )


# =========================================================
# VIRTUAL TRY-ON RESULT
# =========================================================

@app.route("/tryon-result")
def tryon_result():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    result_relative = session.get(
        "tryon_result"
    )


    outfit_id = session.get(
        "tryon_outfit_id"
    )


    if not result_relative:

        flash(
            "No virtual try-on result is available.",
            "error"
        )

        return redirect(
            url_for("recommendations")
        )


    result_path = (
        BASE_DIR
        / result_relative
    )


    if not result_path.exists():

        flash(
            "Virtual try-on result could not be found.",
            "error"
        )

        return redirect(
            url_for("recommendations")
        )


    connection = get_connection()

    try:

        outfit_row = connection.execute(
            """
            SELECT *
            FROM clothing
            WHERE outfit_id = ?
            """,
            (
                outfit_id,
            )
        ).fetchone()

    finally:

        connection.close()


    if outfit_row is None:

        flash(
            "The selected outfit could not be found.",
            "error"
        )

        return redirect(
            url_for("recommendations")
        )


    return render_template(
        "tryon_result.html",
        result_image=url_for(
            "serve_tryon_result"
        ) + f"?t={int(time.time())}",
        outfit=dict(
            outfit_row
        )
    )


# =========================================================
# SERVE TRY-ON RESULT IMAGE
# =========================================================

@app.route(
    "/tryon-result-image"
)
def serve_tryon_result():

    if "user_id" not in session:

        return "", 401


    result_relative = session.get(
        "tryon_result"
    )


    if not result_relative:

        return "", 404


    result_path = (
        BASE_DIR
        / result_relative
    )


    if not result_path.exists():

        return "", 404


    resp = send_file(
        result_path,
        mimetype="image/png"
    )
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


# =========================================================
# FAVOURITES
# =========================================================

@app.route("/favourites")
def favourites():

    if "user_id" not in session:

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT
                clothing.*
            FROM favourites

            INNER JOIN clothing

                ON clothing.id =
                    favourites.clothing_id

            WHERE favourites.user_id = ?

            ORDER BY
                favourites.created_at DESC
            """,

            (
                session["user_id"],
            )
        ).fetchall()

    finally:

        connection.close()


    favourites_list = [
        dict(row)
        for row in rows
    ]


    return render_template(

        "favourites.html",

        favourites=
            favourites_list
    )


# =========================================================
# PRIVACY
# =========================================================

@app.route("/privacy")
def privacy():

    return render_template(
        "privacy.html"
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    return {

        "status": "ok",

        "body_analysis_available":
            BODY_ANALYSIS_AVAILABLE
    }


# =========================================================
# FILE TOO LARGE
# =========================================================

@app.errorhandler(413)
def request_entity_too_large(
    error
):

    flash(
        "The uploaded file is too large.",
        "error"
    )

    return redirect(
        url_for("upload")
    )


# =========================================================
# GOOGLE OAUTH — FIREBASE AUTH ENDPOINT
# =========================================================

@app.route("/auth/google", methods=["POST"])
def google_auth():
    """
    Receive Firebase ID token from the Google Sign-In popup (client JS),
    verify it server-side, create/update user record in SQLite + Firestore,
    and establish a session.
    """
    data = request.get_json(silent=True) or {}
    id_token = data.get("idToken", "").strip()

    if not id_token:
        return jsonify({"success": False, "error": "No ID token provided."})

    try:
        google_info = verify_google_id_token(id_token)
    except Exception as e:
        print(f"[Google OAuth] Token verification error: {e}")
        return jsonify({"success": False, "error": "Google authentication could not be verified."})

    email = (google_info.get("email") or "").strip().lower()
    if not email:
        return jsonify({"success": False, "error": "No email address found in Google account."})

    try:
        user = FirestoreRepository.save_google_user(google_info)
    except Exception as e:
        print(f"[Google OAuth] User save error: {e}")
        return jsonify({"success": False, "error": "Could not create user record."})

    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]
    session["user_email"] = user["email"]
    session["user_name"] = user["full_name"]
    session["user_role"] = user.get("role", "user")
    session["google_auth"] = True

    # Redirect admin users to admin panel, regular users directly to home catalog
    redirect_url = url_for("admin_dashboard") if user.get("role") == "admin" else url_for("home")

    return jsonify({
        "success": True,
        "redirect": redirect_url,
        "name": user["full_name"],
        "email": user["email"],
        "role": user.get("role", "user")
    })


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@admin_required
def admin_dashboard():
    """
    Secure admin panel: inventory management, payment config, orders.
    """
    products = FirestoreRepository.get_all_products()
    orders = FirestoreRepository.get_all_orders()
    master_upi = get_master_upi_id()
    merchant = get_merchant_name()

    # Pre-render a sample QR for testing in the dashboard
    test_qr = generate_order_upi_qr("TEST-ORDER", 1499.00, merchant)

    return render_template(
        "admin/dashboard.html",
        products=products,
        orders=orders,
        master_upi_id=master_upi,
        merchant_name=merchant,
        test_qr_base64=test_qr["qr_base64"],
        test_payload=test_qr["payload"]
    )


# =========================================================
# ADMIN — UPDATE MASTER UPI CONFIGURATION
# =========================================================

@app.route("/admin/update-upi", methods=["POST"])
@admin_required
def admin_update_upi():
    upi_id = request.form.get("master_upi_id", "").strip()
    merchant_name = request.form.get("merchant_name", "").strip()

    try:
        update_master_upi_config(upi_id, merchant_name)
        flash(
            f"Master Google Pay UPI updated successfully: {upi_id}",
            "success"
        )
    except ValueError as e:
        flash(str(e), "error")

    return redirect(url_for("admin_dashboard"))


# =========================================================
# ADMIN — ADD PRODUCT (GET: form, POST: save to Firebase + DB)
# =========================================================

@app.route("/admin/products/add", methods=["GET", "POST"])
@admin_required
def admin_product_add():
    if request.method == "POST":
        outfit_name = request.form.get("outfit_name", "").strip()
        outfit_id = request.form.get("outfit_id", "").strip()
        category = request.form.get("category", "Women").strip()
        clothing_type = request.form.get("clothing_type", "Top").strip()
        price = request.form.get("price", "999").strip()
        brand = request.form.get("brand", "AI Style").strip()
        colour = request.form.get("colour", "").strip()
        fit = request.form.get("fit", "").strip()
        description = request.form.get("description", "").strip()
        sizes = request.form.getlist("sizes") or ["S", "M", "L", "XL"]
        face_target = request.form.get("face_target", "").strip()

        # Preserve form data if validation fails
        form_data = dict(request.form)
        form_data["sizes_list"] = sizes

        if not outfit_name:
            flash("Outfit name is required.", "error")
            return render_template("admin/product_form.html", product=form_data)

        # Validate outfit_id uniqueness upfront if manually specified
        if outfit_id:
            conn = get_connection()
            try:
                existing = conn.execute(
                    "SELECT id, outfit_name FROM clothing WHERE outfit_id = ?",
                    (outfit_id,)
                ).fetchone()
                if existing:
                    flash(
                        f"Outfit SKU / ID '{outfit_id}' is already used by '{existing['outfit_name']}'. "
                        "Please provide a different ID or leave it empty to auto-generate.",
                        "error"
                    )
                    return render_template("admin/product_form.html", product=form_data)
            finally:
                conn.close()

        # Handle clothing image upload to Firebase Storage / local
        clothing_file = request.files.get("clothing_image")
        tryon_file = request.files.get("tryon_image")

        image_path = ""
        tryon_image_path = ""

        if clothing_file and clothing_file.filename and allowed_file(clothing_file.filename):
            fname = secure_filename(clothing_file.filename)
            image_path = upload_clothing_asset(clothing_file, folder="clothing", custom_filename=fname)

        if tryon_file and tryon_file.filename and allowed_file(tryon_file.filename):
            fname = secure_filename(tryon_file.filename)
            tryon_image_path = upload_clothing_asset(tryon_file, folder="clothing", custom_filename=fname)

        if not tryon_image_path and image_path:
            tryon_image_path = image_path

        try:
            product = FirestoreRepository.create_product({
                "outfit_id": outfit_id,  # When empty, FirestoreRepository auto-generates collision-free sequential SKU
                "outfit_name": outfit_name,
                "category": category,
                "clothing_type": clothing_type,
                "price": float(price or 0),
                "brand": brand,
                "colour": colour,
                "fit": fit,
                "description": description,
                "available_sizes": ",".join(sizes),
                "image_path": image_path,
                "tryon_image_path": tryon_image_path,
                "face_target": face_target,
            })
        except Exception as err:
            flash(f"Error saving product to database: {err}", "error")
            return render_template("admin/product_form.html", product=form_data)

        flash(
            f"'{outfit_name}' (SKU: {product.get('outfit_id', outfit_id)}) successfully added to catalog & storage.",
            "success"
        )
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/product_form.html", product=None)


# =========================================================
# ADMIN — EDIT PRODUCT
# =========================================================

@app.route("/admin/products/<int:clothing_id>/edit", methods=["GET", "POST"])
@admin_required
def admin_product_edit(clothing_id):
    product = FirestoreRepository.get_product(clothing_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        outfit_name = request.form.get("outfit_name", "").strip()
        category = request.form.get("category", product["category"])
        clothing_type = request.form.get("clothing_type", product.get("clothing_type", ""))
        price = request.form.get("price", product.get("price", 0))
        brand = request.form.get("brand", product.get("brand", ""))
        colour = request.form.get("colour", product.get("colour", ""))
        fit = request.form.get("fit", product.get("fit", ""))
        description = request.form.get("description", product.get("description", ""))
        sizes = request.form.getlist("sizes") or ["S", "M", "L", "XL"]
        face_target = request.form.get("face_target", product.get("face_target", "")).strip()

        update_data = {
            "outfit_name": outfit_name,
            "category": category,
            "clothing_type": clothing_type,
            "price": float(price or 0),
            "brand": brand,
            "colour": colour,
            "fit": fit,
            "description": description,
            "available_sizes": ",".join(sizes),
            "face_target": face_target,
        }

        # Handle optional new image uploads
        clothing_file = request.files.get("clothing_image")
        tryon_file = request.files.get("tryon_image")

        if clothing_file and clothing_file.filename and allowed_file(clothing_file.filename):
            fname = secure_filename(clothing_file.filename)
            update_data["image_path"] = upload_clothing_asset(
                clothing_file, folder="clothing", custom_filename=fname
            )

        if tryon_file and tryon_file.filename and allowed_file(tryon_file.filename):
            fname = secure_filename(tryon_file.filename)
            update_data["tryon_image_path"] = upload_clothing_asset(
                tryon_file, folder="clothing", custom_filename=fname
            )

        FirestoreRepository.update_product(clothing_id, update_data)
        flash(f"'{outfit_name}' updated successfully.", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin/product_form.html", product=product)


# =========================================================
# ADMIN — DELETE PRODUCT
# =========================================================

@app.route("/admin/products/<int:clothing_id>/delete", methods=["POST"])
@admin_required
def admin_product_delete(clothing_id):
    product = FirestoreRepository.get_product(clothing_id)
    if product:
        # Delete from local file database & remove files from disk
        LocalClothingAssetDB.delete_clothing(clothing_id)
        FirestoreRepository.delete_product(clothing_id)
        flash(
            f"'{product.get('outfit_name', 'Product')}' deleted from local database & storage.",
            "success"
        )
    else:
        flash("Product not found.", "error")
    return redirect(url_for("admin_dashboard"))


# =========================================================
# CHECKOUT — SELECT SIZE + FULL DELIVERY ADDRESS + GEOLOCATION
# =========================================================

@app.route("/checkout")
@app.route("/checkout/<clothing_id>")
@login_required
def checkout(clothing_id=None):
    if not clothing_id:
        clothing_id = request.args.get("clothing_id", "").strip()
    if not clothing_id:
        flash("Please select an outfit first.", "error")
        return redirect(url_for("recommendations"))

    product = FirestoreRepository.get_product(clothing_id)
    if not product:
        flash("Product not found.", "error")
        return redirect(url_for("recommendations"))

    user = get_current_user()
    return render_template("checkout.html", product=product, user=user)


# =========================================================
# CHECKOUT — PROCESS FORM SUBMISSION → CREATE ORDER → PAYMENT
# =========================================================

@app.route("/checkout/submit", methods=["POST"])
@login_required
def checkout_submit():
    clothing_id = request.form.get("clothing_id", "").strip()
    size = request.form.get("size", "M").strip()
    delivery_name = request.form.get("delivery_name", "").strip()
    delivery_phone = request.form.get("delivery_phone", "").strip()
    delivery_address_line1 = request.form.get("delivery_address_line1", "").strip()
    delivery_address_line2 = request.form.get("delivery_address_line2", "").strip()
    delivery_city = request.form.get("delivery_city", "").strip()
    delivery_state = request.form.get("delivery_state", "").strip()
    delivery_postal_code = request.form.get("delivery_postal_code", "").strip()
    latitude = request.form.get("latitude", "").strip()
    longitude = request.form.get("longitude", "").strip()
    location_accuracy = request.form.get("location_accuracy", "").strip()

    # Strict PIN code validation (6-digit Indian PIN)
    import re
    if not re.match(r"^[1-9][0-9]{5}$", delivery_postal_code):
        flash(
            "Invalid PIN Code. Please enter a valid 6-digit Indian postal code.",
            "error"
        )
        product = FirestoreRepository.get_product(clothing_id)
        user = get_current_user()
        return render_template("checkout.html", product=product, user=user)

    # Validate required delivery fields
    if not all([delivery_name, delivery_phone, delivery_address_line1,
                delivery_city, delivery_state, delivery_postal_code]):
        flash("Please fill all required delivery address fields.", "error")
        product = FirestoreRepository.get_product(clothing_id)
        user = get_current_user()
        return render_template("checkout.html", product=product, user=user)

    product = FirestoreRepository.get_product(clothing_id)
    if not product:
        flash("Selected product not found.", "error")
        return redirect(url_for("recommendations"))

    user_id = session["user_id"]
    user_email = session.get("user_email", "")
    order_id = f"ORD-{int(time.time())}-{os.urandom(2).hex().upper()}"

    order = FirestoreRepository.create_order({
        "order_id": order_id,
        "user_id": user_id,
        "user_email": user_email,
        "clothing_id": clothing_id,
        "product_name": product.get("outfit_name", ""),
        "size": size,
        "quantity": 1,
        "price": product.get("price", 0),
        "delivery_name": delivery_name,
        "delivery_phone": delivery_phone,
        "delivery_address_line1": delivery_address_line1,
        "delivery_address_line2": delivery_address_line2,
        "delivery_city": delivery_city,
        "delivery_state": delivery_state,
        "delivery_postal_code": delivery_postal_code,
        "latitude": float(latitude) if latitude else None,
        "longitude": float(longitude) if longitude else None,
        "location_accuracy": float(location_accuracy) if location_accuracy else None,
        "payment_method": "UPI",
        "payment_status": "PENDING"
    })

    # Redirect to payment page
    return redirect(url_for("payment", order_id=order_id))


# =========================================================
# PAYMENT — DYNAMIC UPI QR CODE GATEWAY
# =========================================================

@app.route("/payment/<order_id>")
@login_required
def payment(order_id):
    """
    Secure payment screen: renders dynamically generated Google Pay UPI QR code
    with the exact order total embedded in the upi:// payload.
    """
    order = FirestoreRepository.get_order(order_id)
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for("recommendations"))

    # Security: Only allow the order owner or admin to view
    if (order.get("user_id") != session["user_id"]
            and session.get("user_role") != "admin"):
        flash("Access denied.", "error")
        return redirect(url_for("recommendations"))

    total = float(order.get("price", 0)) * int(order.get("quantity", 1))
    qr_data = generate_order_upi_qr(order_id, total)

    return render_template("payment.html", order=order, qr_data=qr_data)


# =========================================================
# PAYMENT — CONFIRM / MARK AS COMPLETED
# =========================================================

@app.route("/payment/<order_id>/confirm", methods=["POST"])
@login_required
def payment_confirm(order_id):
    """
    Mark order payment as COMPLETED after user confirms they've paid via UPI.
    """
    order = FirestoreRepository.get_order(order_id)
    if not order:
        flash("Order not found.", "error")
        return redirect(url_for("recommendations"))

    upi_ref = request.form.get("upi_reference_id", "").strip()
    if not upi_ref:
        # Generate a reference ID if none supplied
        upi_ref = f"AISTYLE{int(time.time())}"

    FirestoreRepository.update_order_payment(
        order_id,
        status="COMPLETED",
        upi_reference_id=upi_ref
    )

    # Refresh order record
    order = FirestoreRepository.get_order(order_id)

    flash("Payment confirmed! Your order has been placed successfully.", "success")
    return render_template("order_success.html", order=order)


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000
    )