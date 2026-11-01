from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file
)

from pathlib import Path
from werkzeug.utils import secure_filename
import os
import uuid
import cv2

from database import get_connection, initialize_database
from security.auth import hash_password, verify_password


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

        return user

    finally:

        connection.close()


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
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
                "register.html"
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
                    "register.html"
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
        "register.html"
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

            session.clear()

            session["user_id"] = (
                user["id"]
            )

            session["user_email"] = (
                user["email"]
            )

            session["user_name"] = (
                user["full_name"]
            )


            flash(
                "Login successful.",
                "success"
            )

            return redirect(
                url_for("profile")
            )


        flash(
            "Invalid email or password.",
            "error"
        )


    return render_template(
        "login.html"
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


    if photo is None:

        flash(
            "Please select or capture a photo.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


    if not photo.filename:

        flash(
            "Please select a valid photo.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


    if not allowed_file(
        photo.filename
    ):

        flash(
            "Only JPG, JPEG, PNG and WEBP images are allowed.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


    # -----------------------------------------------------
    # FILE SIZE
    # -----------------------------------------------------

    photo.stream.seek(
        0,
        os.SEEK_END
    )

    file_size = (
        photo.stream.tell()
    )

    photo.stream.seek(0)


    if file_size > MAX_FILE_SIZE:

        flash(
            "Photo must be smaller than 10 MB.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


    # -----------------------------------------------------
    # SAVE PHOTO WITH UNIQUE NAME
    # -----------------------------------------------------

    extension = (
        photo.filename
        .rsplit(".", 1)[1]
        .lower()
    )


    unique_name = (
        f"user_{session['user_id']}_"
        f"{uuid.uuid4().hex}."
        f"{extension}"
    )


    safe_name = secure_filename(
        unique_name
    )


    photo_path = (
        TEMP_PHOTO_DIR
        / safe_name
    )


    photo.save(
        photo_path
    )


    # -----------------------------------------------------
    # VALIDATE IMAGE
    # -----------------------------------------------------

    if not validate_image_file(
        photo_path
    ):

        try:

            photo_path.unlink()

        except Exception:

            pass


        flash(
            "The uploaded file is not a valid image.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


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
# USER PHOTO
# =========================================================

@app.route("/user-photo")
def user_photo():

    if "user_id" not in session:

        return "", 401


    photo_relative = session.get(
        "uploaded_photo"
    )


    if not photo_relative:

        return "", 404


    photo_path = (
        BASE_DIR
        / photo_relative
    )


    if not photo_path.exists():

        return "", 404


    return send_file(
        photo_path
    )


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

                sp.height_cm

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

        flash(
            "Please login first.",
            "error"
        )

        return redirect(
            url_for("login")
        )


    clothing_id = request.args.get(
        "clothing_id",
        ""
    ).strip()


    if not clothing_id:

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


    photo_relative = session.get(
        "uploaded_photo"
    )


    photo_exists = False


    if photo_relative:

        photo_path = (
            BASE_DIR
            / photo_relative
        )

        photo_exists = (
            photo_path.exists()
        )


    return render_template(
        "tryon.html",

        outfit=outfit,

        photo_exists=
            photo_exists
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


    photo_relative = session.get(
        "uploaded_photo"
    )


    if not photo_relative:

        flash(
            "Please upload your photo first.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


    person_image = (
        BASE_DIR
        / photo_relative
    )


    if not person_image.exists():

        flash(
            "Your uploaded photo could not be found.",
            "error"
        )

        return redirect(
            url_for("upload")
        )


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
    )


    if not tryon_image_path:

        flash(
            "This outfit does not have a virtual try-on garment image yet.",
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
            "The garment image for this outfit could not be found.",
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
                )
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

        print(
            "VIRTUAL TRY-ON ERROR"
        )

        print(error)

        print("=" * 40)


        flash(
            "Virtual try-on could not be generated right now. "
            "The hosted AI model may be busy or temporarily unavailable.",
            "error"
        )


        return redirect(
            url_for(
                "outfit",
                outfit_id=
                    outfit["outfit_id"]
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
        ),

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


    return send_file(
        result_path
    )


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
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(

        debug=True,

        host="127.0.0.1",

        port=5000
    )