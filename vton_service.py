import os
import sys
import json
import concurrent.futures
from pathlib import Path

# Ensure UTF-8 output on Windows console to prevent charmap encoding errors
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Load .env (GEMINI_API_KEY) when this module is used standalone
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:
    pass
from shutil import copy2

from PIL import Image, ImageDraw, ImageFilter

import numpy as np
import cv2

from gradio_client import Client, handle_file


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "storage" / "temp" / "vton_results"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# IDM-VTON CLIENT
# ============================================================

def get_vton_client():
    return Client("yisol/IDM-VTON")


# ============================================================
# HELPER: GET LANDMARK POINT
# ============================================================

def _safe_point(landmark, width, height):
    x = int(max(0, min(width - 1, landmark.x * width)))
    y = int(max(0, min(height - 1, landmark.y * height)))

    visibility = getattr(landmark, "visibility", 1.0)

    return x, y, visibility


# ============================================================
# BUILD BETTER LOWER BODY MASK
#
# This mask focuses mainly on:
# - pelvis
# - left thigh
# - right thigh
# - left leg
# - right leg
#
# It avoids creating one huge rectangle around the whole
# lower body, which was causing the bag/arms/artifacts problem.
# ============================================================

def build_lower_body_mask(person_image):

    try:
        import mediapipe as mp
    except Exception as error:
        raise RuntimeError(
            "MediaPipe is required for lower-body virtual try-on."
        ) from error

    person_path = Path(person_image)

    image = cv2.imread(str(person_path))

    if image is None:
        raise FileNotFoundError(
            f"Could not read person image:\n{person_path}"
        )

    height, width = image.shape[:2]

    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    mp_pose = mp.solutions.pose

    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=True,
        min_detection_confidence=0.5
    ) as pose:

        result = pose.process(rgb_image)

    if not result.pose_landmarks:
        raise RuntimeError(
            "Could not detect the person's pose. "
            "Please use a clear full-body photo."
        )

    landmarks = result.pose_landmarks.landmark

    # MediaPipe pose landmark indexes
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    LEFT_HIP = 23
    RIGHT_HIP = 24

    LEFT_KNEE = 25
    RIGHT_KNEE = 26

    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    # --------------------------------------------------------
    # Read landmarks
    # --------------------------------------------------------

    ls = _safe_point(
        landmarks[LEFT_SHOULDER],
        width,
        height
    )

    rs = _safe_point(
        landmarks[RIGHT_SHOULDER],
        width,
        height
    )

    lh = _safe_point(
        landmarks[LEFT_HIP],
        width,
        height
    )

    rh = _safe_point(
        landmarks[RIGHT_HIP],
        width,
        height
    )

    lk = _safe_point(
        landmarks[LEFT_KNEE],
        width,
        height
    )

    rk = _safe_point(
        landmarks[RIGHT_KNEE],
        width,
        height
    )

    la = _safe_point(
        landmarks[LEFT_ANKLE],
        width,
        height
    )

    ra = _safe_point(
        landmarks[RIGHT_ANKLE],
        width,
        height
    )

    # Check important landmarks
    required_points = [
        lh, rh,
        lk, rk,
        la, ra
    ]

    for point in required_points:
        if point[2] < 0.35:
            raise RuntimeError(
                "Lower-body landmarks are not clear enough. "
                "Please use a full-body photo with both legs visible."
            )

    # --------------------------------------------------------
    # Extract x/y only
    # --------------------------------------------------------

    left_hip = np.array([lh[0], lh[1]], dtype=np.float32)
    right_hip = np.array([rh[0], rh[1]], dtype=np.float32)

    left_knee = np.array([lk[0], lk[1]], dtype=np.float32)
    right_knee = np.array([rk[0], rk[1]], dtype=np.float32)

    left_ankle = np.array([la[0], la[1]], dtype=np.float32)
    right_ankle = np.array([ra[0], ra[1]], dtype=np.float32)

    # --------------------------------------------------------
    # Body measurements
    # --------------------------------------------------------

    hip_distance = float(
        np.linalg.norm(right_hip - left_hip)
    )

    if hip_distance < 20:
        raise RuntimeError(
            "Could not determine the hip width properly."
        )

    shoulder_y = min(ls[1], rs[1])

    hip_y = min(lh[1], rh[1])

    knee_y = max(lk[1], rk[1])

    ankle_y = max(la[1], ra[1])

    # --------------------------------------------------------
    # Create empty mask
    # --------------------------------------------------------

    mask = np.zeros(
        (height, width),
        dtype=np.uint8
    )

    # ========================================================
    # 1. PELVIS / WAIST AREA
    #
    # Keep it relatively narrow so that arms/bag are not
    # included.
    # ========================================================

    hip_center = (
        (left_hip + right_hip) / 2.0
    )

    pelvis_top_y = int(
        hip_center[1] - hip_distance * 0.18
    )

    pelvis_bottom_y = int(
        hip_center[1] + hip_distance * 0.55
    )

    pelvis_left_x = int(
        hip_center[0] - hip_distance * 0.62
    )

    pelvis_right_x = int(
        hip_center[0] + hip_distance * 0.62
    )

    pelvis_left_x = max(
        0,
        pelvis_left_x
    )

    pelvis_right_x = min(
        width - 1,
        pelvis_right_x
    )

    pelvis_top_y = max(
        0,
        pelvis_top_y
    )

    pelvis_bottom_y = min(
        height - 1,
        pelvis_bottom_y
    )

    cv2.rectangle(
        mask,
        (
            pelvis_left_x,
            pelvis_top_y
        ),
        (
            pelvis_right_x,
            pelvis_bottom_y
        ),
        255,
        -1
    )

    # ========================================================
    # 2. FUNCTION TO CREATE A NARROW LEG CORRIDOR
    # ========================================================

    def create_leg_corridor(
        hip_point,
        knee_point,
        ankle_point,
        hip_width,
        knee_width,
        ankle_width
    ):

        points = [
            hip_point,
            knee_point,
            ankle_point
        ]

        widths = [
            hip_width,
            knee_width,
            ankle_width
        ]

        left_side = []
        right_side = []

        for index, point in enumerate(points):

            if index == 0:
                direction = points[1] - points[0]

            elif index == len(points) - 1:
                direction = points[-1] - points[-2]

            else:
                direction = points[index + 1] - points[index - 1]

            length = np.linalg.norm(direction)

            if length < 1:
                direction = np.array(
                    [0.0, 1.0],
                    dtype=np.float32
                )
                length = 1

            direction = direction / length

            # perpendicular vector
            perpendicular = np.array(
                [-direction[1], direction[0]],
                dtype=np.float32
            )

            half_width = widths[index] / 2.0

            left_side.append(
                point + perpendicular * half_width
            )

            right_side.append(
                point - perpendicular * half_width
            )

        polygon_points = (
            left_side +
            right_side[::-1]
        )

        polygon_points = np.array(
            polygon_points,
            dtype=np.int32
        )

        return polygon_points

    # ========================================================
    # 3. LEFT LEG
    # ========================================================

    left_leg_polygon = create_leg_corridor(
        left_hip,
        left_knee,
        left_ankle,

        hip_width=hip_distance * 0.62,
        knee_width=hip_distance * 0.43,
        ankle_width=hip_distance * 0.34
    )

    cv2.fillPoly(
        mask,
        [left_leg_polygon],
        255
    )

    # ========================================================
    # 4. RIGHT LEG
    # ========================================================

    right_leg_polygon = create_leg_corridor(
        right_hip,
        right_knee,
        right_ankle,

        hip_width=hip_distance * 0.62,
        knee_width=hip_distance * 0.43,
        ankle_width=hip_distance * 0.34
    )

    cv2.fillPoly(
        mask,
        [right_leg_polygon],
        255
    )

    # ========================================================
    # 5. CONNECT UPPER THIGHS
    #
    # Adds the area between the two legs but keeps it
    # restricted around the hips/thighs.
    # ========================================================

    inner_thigh_polygon = np.array(
        [
            [
                int(left_hip[0]),
                int(left_hip[1])
            ],
            [
                int(right_hip[0]),
                int(right_hip[1])
            ],
            [
                int(right_knee[0]),
                int(right_knee[1])
            ],
            [
                int(left_knee[0]),
                int(left_knee[1])
            ]
        ],
        dtype=np.int32
    )

    cv2.fillPoly(
        mask,
        [inner_thigh_polygon],
        255
    )

    # ========================================================
    # 6. USE MEDIA PIPE SEGMENTATION AS A SAFETY BOUNDARY
    #
    # Important:
    # We use segmentation ONLY to remove areas outside the
    # person's body.
    #
    # We do NOT use a huge segmentation mask as the final
    # lower-body mask.
    # ========================================================

    if result.segmentation_mask is not None:

        segmentation = (
            result.segmentation_mask > 0.45
        ).astype(np.uint8) * 255

        # Small morphological cleanup
        kernel = np.ones(
            (5, 5),
            np.uint8
        )

        segmentation = cv2.morphologyEx(
            segmentation,
            cv2.MORPH_CLOSE,
            kernel
        )

        # Keep only our carefully designed lower-body region
        mask = np.where(
            segmentation > 0,
            mask,
            0
        ).astype(np.uint8)

    # ========================================================
    # 7. REMOVE EVERYTHING ABOVE HIP REGION
    #
    # This prevents the pants mask from accidentally entering
    # the shirt/arms area.
    # ========================================================

    safe_top = int(
        hip_y - hip_distance * 0.22
    )

    safe_top = max(
        0,
        safe_top
    )

    mask[:safe_top, :] = 0

    # ========================================================
    # 8. REMOVE EXTREME OUTER SIDES
    #
    # This protects against bags/accessories near the legs.
    # ========================================================

    body_center_x = int(
        hip_center[0]
    )

    max_side = int(
        hip_distance * 1.15
    )

    outer_left = max(
        0,
        body_center_x - max_side
    )

    outer_right = min(
        width,
        body_center_x + max_side
    )

    side_mask = np.zeros_like(mask)

    side_mask[:, outer_left:outer_right] = 255

    mask = cv2.bitwise_and(
        mask,
        side_mask
    )

    # ========================================================
    # 9. CLEAN MASK
    # ========================================================

    kernel_small = np.ones(
        (7, 7),
        np.uint8
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel_small
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        np.ones((3, 3), np.uint8)
    )

    # Slight blur for smoother clothing boundary
    pil_mask = Image.fromarray(
        mask
    )

    pil_mask = pil_mask.filter(
        ImageFilter.GaussianBlur(
            radius=1.2
        )
    )

    # Convert to clean binary mask
    pil_mask = pil_mask.point(
        lambda value:
        255 if value >= 80 else 0
    )

    return pil_mask


def _run_with_timeout(func, args=(), kwargs=None, timeout_sec=8):
    """Executes a function with a strict non-blocking timeout to prevent hung remote network calls."""
    if kwargs is None:
        kwargs = {}
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func, *args, **kwargs)
    try:
        return future.result(timeout=timeout_sec)
    finally:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass


# ============================================================
# RUN IDM-VTON
# ============================================================

def run_idm_vton(
    person_image,
    garment_image,
    garment_description,
    custom_mask=None,
    use_crop=True
):

    person_image = Path(
        person_image
    )

    garment_image = Path(
        garment_image
    )

    if not person_image.exists():
        raise FileNotFoundError(
            f"Person image not found:\n{person_image}"
        )

    if not garment_image.exists():
        raise FileNotFoundError(
            f"Garment image not found:\n{garment_image}"
        )

    print("Connecting to IDM-VTON...")

    client = get_vton_client()

    print("Connected successfully.")

    # ========================================================
    # AUTOMATIC MASK
    # ========================================================

    if custom_mask is None:

        human_editor = {
            "background": handle_file(
                str(person_image)
            ),
            "layers": [],
            "composite": None
        }

        use_auto_mask = True

    # ========================================================
    # CUSTOM MASK
    # ========================================================

    else:

        custom_mask = Path(
            custom_mask
        )

        if not custom_mask.exists():
            raise FileNotFoundError(
                f"Mask not found:\n{custom_mask}"
            )

        human_editor = {
            "background": handle_file(
                str(person_image)
            ),
            "layers": [
                handle_file(
                    str(custom_mask)
                )
            ],
            "composite": None
        }

        use_auto_mask = False

    print(
        f"Garment: {garment_image.name}"
    )

    print(
        f"Description: {garment_description}"
    )

    print(
        f"Automatic mask: {use_auto_mask}"
    )

    print(
        f"Crop enabled: {use_crop}"
    )

    print(
        "Generating virtual try-on..."
    )

    result = client.predict(
        human_editor,
        handle_file(
            str(garment_image)
        ),
        garment_description,
        use_auto_mask,
        use_crop,
        30,
        42,
        api_name="/tryon"
    )

    generated_image = result[0]

    masked_image = result[1]

    return (
        generated_image,
        masked_image
    )


# ============================================================
# GEMINI AI FACE-SWAP VIRTUAL TRY-ON (PRIMARY PIPELINE)
# ============================================================

def gemini_face_swap_tryon(
    person_image,
    garment_image,
    output_path=None,
    mask_path=None,
    garment_description="outfit"
):
    """
    Gemini 2.0 Flash multimodal pipeline for virtual try-on with face-swap.
    Sends both the user's photo and the clothing product image to Gemini,
    instructing it to overlay the garment onto the user's body while
    replacing the model's face with the user's face, clothing intact.

    Requires GEMINI_API_KEY environment variable to be set.
    Raises RuntimeError if key is missing or API returns no image.
    """
    import base64
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError(
            "google-generativeai package is not installed. "
            "Run: pip install google-generativeai"
        )

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. "
            "Set it to use Gemini-powered virtual try-on."
        )

    genai.configure(api_key=api_key)

    person_path = Path(person_image)
    garment_path = Path(garment_image)
    final_file = Path(output_path) if output_path else OUTPUT_DIR / "tryon_result.png"
    final_mask_file = Path(mask_path) if mask_path else OUTPUT_DIR / "tryon_mask.png"

    if not person_path.exists():
        raise FileNotFoundError(f"Person image not found: {person_path}")
    if not garment_path.exists():
        raise FileNotFoundError(f"Garment image not found: {garment_path}")

    # Read images as base64 inline data
    with open(str(person_path), "rb") as f:
        person_b64 = base64.b64encode(f.read()).decode()
    with open(str(garment_path), "rb") as f:
        garment_b64 = base64.b64encode(f.read()).decode()

    person_mime = (
        "image/jpeg"
        if person_path.suffix.lower() in [".jpg", ".jpeg"]
        else "image/png"
    )
    garment_mime = (
        "image/jpeg"
        if garment_path.suffix.lower() in [".jpg", ".jpeg"]
        else "image/png"
    )

    # Candidate models for virtual try-on image generation
    candidate_models = [
        "gemini-2.5-flash-image",
        "gemini-3.1-flash-image",
        "gemini-3-pro-image",
        "gemini-2.0-flash-exp"
    ]

    prompt = (
        f"You are a photorealistic virtual fashion try-on assistant. "
        f"I am providing two images: "
        f"(1) a person's photo (Image 1) and "
        f"(2) a clothing item — {garment_description} (Image 2). "
        f"Generate a single photorealistic image showing the person from Image 1 "
        f"wearing the clothing from Image 2. "
        f"CRITICAL REQUIREMENTS: "
        f"1. Preserve the person's face from Image 1 exactly — same facial features, "
        f"skin tone, hair, and expression. "
        f"2. If Image 2 shows a model wearing the clothing, replace that model's face "
        f"and body with the person from Image 1, keeping the clothing intact. "
        f"3. Keep the clothing item from Image 2 completely intact — original colors, "
        f"patterns, texture, cut, and design. "
        f"4. Maintain natural body proportions and realistic draping of the clothing "
        f"on the person's body. "
        f"5. Match the lighting and shadows naturally. "
        f"6. Output ONLY the final try-on image. No text, no watermarks, no borders."
    )

    last_error = None
    for model_name in candidate_models:
        try:
            print(f"[Gemini Try-On] Attempting generation with model: {model_name}...")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                [
                    {"inline_data": {"mime_type": person_mime, "data": person_b64}},
                    {"inline_data": {"mime_type": garment_mime, "data": garment_b64}},
                    prompt,
                ]
            )

            # Extract generated image from response parts
            if response and hasattr(response, "candidates") and response.candidates:
                for candidate in response.candidates:
                    for part in candidate.content.parts:
                        if hasattr(part, "inline_data") and part.inline_data:
                            img_bytes = base64.b64decode(part.inline_data.data)
                            with open(str(final_file), "wb") as out:
                                out.write(img_bytes)
                            # Write a blank white mask as placeholder
                            Image.new("L", (512, 512), 255).save(str(final_mask_file))
                            print(f"[Gemini Try-On] Success with {model_name} → {final_file}")
                            return final_file, final_mask_file
        except Exception as err:
            print(f"[Gemini Try-On] Model {model_name} failed: {err}")
            last_error = err
            err_str = str(err).lower()
            if "429" in err_str or "quota" in err_str or "billing" in err_str or "limit: 0" in err_str:
                print("[Gemini Try-On] Quota limit detected on free tier, switching to next pipeline.")
                break

    raise RuntimeError(
        f"Gemini image generation could not produce an image. Last error: {last_error}"
    )


# ============================================================
# NEURAL INPAINTING & PHOTOREALISTIC TRY-ON ENGINE (FALLBACK / LOCAL)
# ============================================================

def neural_inpaint_tryon(
    person_image,
    garment_image,
    output_path=None,
    mask_path=None,
    garment_description="outfit",
    face_target=None
):
    """
    Photorealistic Virtual Fitting & Face-Swap Pipeline:
    - If the admin marked a custom face placement oval target on this garment:
      Pins the user's face oval directly onto that marked target with exact dimensions,
      angle, lighting harmonization, and seamless Poisson blending.
    - If the outfit image shows a model wearing the clothing:
      Performs an intelligent, seamless face-swap replacing the model's face with
      the user's face, matching skin tones, lighting, and complexion via Poisson blending.
    - If the outfit image has a neckline/collar:
      Positions the user's face template right above the garment's collar line.
    """
    person_path = Path(person_image)
    garment_path = Path(garment_image)

    final_file = Path(output_path) if output_path else OUTPUT_DIR / "tryon_result.png"
    final_mask_file = Path(mask_path) if mask_path else OUTPUT_DIR / "tryon_mask.png"

    from PIL import ImageOps
    raw_person = Image.open(str(person_path))
    person_img = ImageOps.exif_transpose(raw_person).convert("RGBA")

    raw_garment = Image.open(str(garment_path))
    garment_img = ImageOps.exif_transpose(raw_garment).convert("RGBA")

    # Convert to OpenCV BGR
    person_rgb = np.array(person_img.convert("RGB"))
    user_bgr = cv2.cvtColor(person_rgb, cv2.COLOR_RGB2BGR)

    garment_rgb = np.array(garment_img.convert("RGB"))
    garment_bgr = cv2.cvtColor(garment_rgb, cv2.COLOR_RGB2BGR)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    # Check if person_image is already an oval face template
    person_arr = np.array(person_img)
    is_oval_template = (
        "face_template" in str(person_path).lower()
        or "oval" in str(person_path).lower()
        or (person_arr.shape[2] == 4 and np.any(person_arr[:, :, 3] == 0))
    )

    # Detect user faces (pick largest)
    u_gray = cv2.cvtColor(user_bgr, cv2.COLOR_BGR2GRAY)
    u_faces = face_cascade.detectMultiScale(u_gray, scaleFactor=1.08, minNeighbors=3)

    if is_oval_template or len(u_faces) == 0:
        # User image is an isolated face template
        if person_arr.shape[2] == 4 and np.any(person_arr[:, :, 3] > 10):
            # Find bounding box of non-transparent face region
            y_indices, x_indices = np.where(person_arr[:, :, 3] > 10)
            if len(y_indices) > 0 and len(x_indices) > 0:
                ux, uy = int(x_indices.min()), int(y_indices.min())
                uw, uh = int(x_indices.max() - ux), int(y_indices.max() - uy)
                u_crop = user_bgr[uy:uy + uh, ux:ux + uw]
            else:
                ux, uy, uw, uh = 0, 0, user_bgr.shape[1], user_bgr.shape[0]
                u_crop = user_bgr
        else:
            ux, uy, uw, uh = 0, 0, user_bgr.shape[1], user_bgr.shape[0]
            u_crop = user_bgr
        user_has_face = True
    else:
        gx, gy, gw, gh = max(u_faces, key=lambda f: f[2] * f[3])
        my = int(gh * 0.14)
        mx = int(gw * 0.10)
        u_crop = user_bgr[
            max(0, gy - my):min(user_bgr.shape[0], gy + gh + my),
            max(0, gx - mx):min(user_bgr.shape[1], gx + gw + mx)
        ]
        uw, uh = u_crop.shape[1], u_crop.shape[0]
        user_has_face = True

    g_h, g_w = garment_bgr.shape[:2]

    # Parse Admin Marked Face Target if supplied
    parsed_target = None
    if face_target:
        try:
            import json
            parsed_target = json.loads(face_target) if isinstance(face_target, str) else face_target
        except Exception as e:
            print(f"[Virtual Fitting] Note parsing face_target: {e}")
            parsed_target = None

    # =========================================================================
    # MODE 0: ADMIN-PINNED FACE PLACEMENT (Admin Marked Oval Target on Garment)
    # =========================================================================
    if parsed_target and user_has_face and (parsed_target.get("x") is not None or parsed_target.get("norm_x") is not None):
        print("[Virtual Fitting] Mode 0: Using Admin Marked Face Pin Target...")

        if parsed_target.get("norm_x") is not None and parsed_target.get("norm_w") is not None:
            tx = int(parsed_target["norm_x"] * g_w)
            ty = int(parsed_target["norm_y"] * g_h)
            tw = max(35, int(parsed_target["norm_w"] * g_w))
            th = max(45, int(parsed_target["norm_h"] * g_h))
        else:
            rec_w = parsed_target.get("img_w") or g_w
            rec_h = parsed_target.get("img_h") or g_h
            scale_x = g_w / float(rec_w)
            scale_y = g_h / float(rec_h)
            tx = int(parsed_target.get("x", 0) * scale_x)
            ty = int(parsed_target.get("y", 0) * scale_y)
            tw = max(35, int(parsed_target.get("width", 80) * scale_x))
            th = max(45, int(parsed_target.get("height", 100) * scale_y))

        angle = float(parsed_target.get("angle") or 0.0)

        # Scale user face template to marked target size
        u_face_resized = cv2.resize(u_crop, (tw, th), interpolation=cv2.INTER_LANCZOS4)

        if abs(angle) > 0.5:
            M = cv2.getRotationMatrix2D((tw / 2, th / 2), angle, 1.0)
            u_face_resized = cv2.warpAffine(u_face_resized, M, (tw, th), borderMode=cv2.BORDER_REPLICATE)

        # Harmonize lighting and skin tone in LAB space
        target_patch = garment_bgr[max(0, ty):min(g_h, ty + th), max(0, tx):min(g_w, tx + tw)]
        if target_patch.shape[0] > 10 and target_patch.shape[1] > 10:
            s_lab = cv2.cvtColor(u_face_resized, cv2.COLOR_BGR2LAB).astype(np.float32)
            t_lab = cv2.cvtColor(target_patch, cv2.COLOR_BGR2LAB).astype(np.float32)
            for c in range(3):
                s_mean, s_std = s_lab[:, :, c].mean(), s_lab[:, :, c].std() + 1e-6
                t_mean, t_std = t_lab[:, :, c].mean(), t_lab[:, :, c].std() + 1e-6
                s_lab[:, :, c] = s_lab[:, :, c] + 0.58 * (((s_lab[:, :, c] - s_mean) * (t_std / s_std) + t_mean) - s_lab[:, :, c])
            s_lab = np.clip(s_lab, 0, 255).astype(np.uint8)
            u_face_blended = cv2.cvtColor(s_lab, cv2.COLOR_LAB2BGR)
        else:
            u_face_blended = u_face_resized

        # Smooth oval feathered mask
        mask = np.zeros((th, tw), dtype=np.uint8)
        cv2.ellipse(
            mask,
            (tw // 2, th // 2),
            (int(tw * 0.46), int(th * 0.48)),
            0, 0, 360, 255, -1
        )

        dest_center = (
            int(tx + tw / 2),
            int(ty + th / 2)
        )

        # Seamless Poisson blending onto the marked position
        try:
            cloned = cv2.seamlessClone(u_face_blended, garment_bgr, mask, dest_center, cv2.NORMAL_CLONE)
        except Exception as clone_err:
            print(f"[Virtual Fitting] SeamlessClone fallback on marked pin: {clone_err}")
            cloned = garment_bgr.copy()
            y1 = max(0, dest_center[1] - th // 2)
            y2 = min(cloned.shape[0], y1 + th)
            x1 = max(0, dest_center[0] - tw // 2)
            x2 = min(cloned.shape[1], x1 + tw)
            norm_mask = (mask[:y2 - y1, :x2 - x1] / 255.0)[:, :, np.newaxis]
            cloned[y1:y2, x1:x2] = (
                cloned[y1:y2, x1:x2] * (1.0 - norm_mask) + u_face_blended[:y2 - y1, :x2 - x1] * norm_mask
            ).astype(np.uint8)

        # Upscale to high-definition 1080p
        h_out, w_out = cloned.shape[:2]
        if h_out < 1080:
            scale = 1080.0 / h_out
            cloned = cv2.resize(cloned, (int(w_out * scale), 1080), interpolation=cv2.INTER_LANCZOS4)

        cv2.imwrite(str(final_file), cloned)
        Image.new("L", (cloned.shape[1], cloned.shape[0]), 255).save(str(final_mask_file))

        print(f"[Virtual Fitting] Face pinned to admin marked oval successfully: {final_file} ({cloned.shape[1]}x{cloned.shape[0]})")
        return final_file, final_mask_file

    # Detect model faces in outfit (check top 42% of image where head is positioned)
    g_gray = cv2.cvtColor(garment_bgr, cv2.COLOR_BGR2GRAY)
    g_faces_all = face_cascade.detectMultiScale(g_gray, scaleFactor=1.08, minNeighbors=3)
    g_faces_top = [f for f in g_faces_all if f[1] < g_h * 0.45]

    # =========================================================================
    # MODE 1: FACE-SWAP ONTO OUTFIT MODEL (When clothing image has a model head)
    # =========================================================================
    if len(g_faces_top) > 0 and user_has_face:
        print("[Virtual Fitting] Mode 1: Face-Swap onto Outfit Model...")
        gx, gy, gw, gh = max(g_faces_top, key=lambda f: f[2] * f[3])

        # Target dimensions matching model's head
        target_w = int(gw * 1.08)
        target_h = int(gh * 1.20)
        u_face_resized = cv2.resize(u_crop, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        # Ambient skin-tone and lighting harmonization in LAB space
        model_patch = garment_bgr[gy:gy + gh, gx:gx + gw]
        if model_patch.shape[0] > 10 and model_patch.shape[1] > 10:
            s_lab = cv2.cvtColor(u_face_resized, cv2.COLOR_BGR2LAB).astype(np.float32)
            t_lab = cv2.cvtColor(model_patch, cv2.COLOR_BGR2LAB).astype(np.float32)
            for c in range(3):
                s_mean, s_std = s_lab[:, :, c].mean(), s_lab[:, :, c].std() + 1e-6
                t_mean, t_std = t_lab[:, :, c].mean(), t_lab[:, :, c].std() + 1e-6
                s_lab[:, :, c] = s_lab[:, :, c] + 0.62 * (((s_lab[:, :, c] - s_mean) * (t_std / s_std) + t_mean) - s_lab[:, :, c])
            s_lab = np.clip(s_lab, 0, 255).astype(np.uint8)
            u_face_blended = cv2.cvtColor(s_lab, cv2.COLOR_LAB2BGR)
        else:
            u_face_blended = u_face_resized

        # Smooth feathered elliptical mask centered on face oval
        mask = np.zeros((target_h, target_w), dtype=np.uint8)
        cv2.ellipse(
            mask,
            (target_w // 2, target_h // 2),
            (int(target_w * 0.44), int(target_h * 0.48)),
            0, 0, 360, 255, -1
        )

        dest_center = (
            int(gx + gw / 2),
            int(gy + gh / 2 + gh * 0.04)
        )

        # Poisson gradient seamless clone
        cloned = cv2.seamlessClone(u_face_blended, garment_bgr, mask, dest_center, cv2.NORMAL_CLONE)

        # Upscale to high-definition portrait resolution (minimum 1080px height)
        h_out, w_out = cloned.shape[:2]
        if h_out < 1080:
            scale = 1080.0 / h_out
            cloned = cv2.resize(cloned, (int(w_out * scale), 1080), interpolation=cv2.INTER_LANCZOS4)

        cv2.imwrite(str(final_file), cloned)
        Image.new("L", (cloned.shape[1], cloned.shape[0]), 255).save(str(final_mask_file))

        print(f"[Virtual Fitting] Face-swap try-on complete: {final_file} ({cloned.shape[1]}x{cloned.shape[0]})")
        return final_file, final_mask_file

    # =========================================================================
    # MODE 1B: COLLAR / NECKLINE FACE MOUNTING (When garment has neck/collar but no model head)
    # =========================================================================
    if user_has_face and g_h > 150:
        print("[Virtual Fitting] Mode 1B: Fitting Face Template to Garment Neckline / Collar...")

        # Size face template proportionally to garment width (face width ~ 32% of outfit width)
        target_w = max(120, int(g_w * 0.32))
        aspect = u_crop.shape[0] / max(1, u_crop.shape[1])
        target_h = int(target_w * aspect)

        u_face_resized = cv2.resize(u_crop, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        # Ambient lighting match with collar fabric
        collar_sample = garment_bgr[int(g_h * 0.10):int(g_h * 0.35), int(g_w * 0.35):int(g_w * 0.65)]
        if collar_sample.shape[0] > 10 and collar_sample.shape[1] > 10:
            s_lab = cv2.cvtColor(u_face_resized, cv2.COLOR_BGR2LAB).astype(np.float32)
            t_lab = cv2.cvtColor(collar_sample, cv2.COLOR_BGR2LAB).astype(np.float32)
            for c in range(3):
                s_mean, s_std = s_lab[:, :, c].mean(), s_lab[:, :, c].std() + 1e-6
                t_mean, t_std = t_lab[:, :, c].mean(), t_lab[:, :, c].std() + 1e-6
                s_lab[:, :, c] = s_lab[:, :, c] + 0.35 * (((s_lab[:, :, c] - s_mean) * (t_std / s_std) + t_mean) - s_lab[:, :, c])
            s_lab = np.clip(s_lab, 0, 255).astype(np.uint8)
            u_face_blended = cv2.cvtColor(s_lab, cv2.COLOR_LAB2BGR)
        else:
            u_face_blended = u_face_resized

        # Pad top of garment if needed to accommodate full head comfortably
        top_head_space = int(target_h * 0.70)
        padded_garment = cv2.copyMakeBorder(
            garment_bgr,
            top_head_space,
            0,
            0,
            0,
            cv2.BORDER_REPLICATE
        )

        # Smooth blurred background for upper border
        blur_band = padded_garment[:top_head_space + 20, :]
        padded_garment[:top_head_space + 20, :] = cv2.GaussianBlur(blur_band, (25, 25), 0)

        # Destination center for face template
        dest_x = padded_garment.shape[1] // 2
        dest_y = top_head_space + int(target_h * 0.28)

        mask = np.zeros((target_h, target_w), dtype=np.uint8)
        cv2.ellipse(
            mask,
            (target_w // 2, target_h // 2),
            (int(target_w * 0.45), int(target_h * 0.48)),
            0, 0, 360, 255, -1
        )

        try:
            cloned = cv2.seamlessClone(u_face_blended, padded_garment, mask, (dest_x, dest_y), cv2.NORMAL_CLONE)
        except Exception:
            # Fallback alpha composite
            cloned = padded_garment.copy()
            y1 = max(0, dest_y - target_h // 2)
            y2 = min(cloned.shape[0], y1 + target_h)
            x1 = max(0, dest_x - target_w // 2)
            x2 = min(cloned.shape[1], x1 + target_w)
            norm_mask = (mask[:y2 - y1, :x2 - x1] / 255.0)[:, :, np.newaxis]
            cloned[y1:y2, x1:x2] = (
                cloned[y1:y2, x1:x2] * (1.0 - norm_mask) + u_face_blended[:y2 - y1, :x2 - x1] * norm_mask
            ).astype(np.uint8)

        # Upscale to high-definition portrait resolution (minimum 1080px height)
        h_out, w_out = cloned.shape[:2]
        if h_out < 1080:
            scale = 1080.0 / h_out
            cloned = cv2.resize(cloned, (int(w_out * scale), 1080), interpolation=cv2.INTER_LANCZOS4)

        cv2.imwrite(str(final_file), cloned)
        Image.new("L", (cloned.shape[1], cloned.shape[0]), 255).save(str(final_mask_file))

        print(f"[Virtual Fitting] Collar-mounted face try-on complete: {final_file} ({cloned.shape[1]}x{cloned.shape[0]})")
        return final_file, final_mask_file

    # =========================================================================
    # MODE 2: GARMENT DRAPING (When clothing is a flat lay/packshot)
    # =========================================================================
    print("[Virtual Fitting] Mode: Garment Draping onto User Photo...")

    # Garment alpha background extraction if not already transparent
    g_arr = np.array(garment_img)
    has_transparency = np.any(g_arr[:, :, 3] < 200)
    if not has_transparency:
        h, w = g_arr.shape[:2]
        corners = [
            g_arr[min(5, h - 1), min(5, w - 1), :3],
            g_arr[min(5, h - 1), max(0, w - 6), :3],
            g_arr[max(0, h - 6), min(5, w - 1), :3],
            g_arr[max(0, h - 6), max(0, w - 6), :3]
        ]
        bg_color = np.median(corners, axis=0).astype(np.float32)
        diff = np.linalg.norm(g_arr[:, :, :3].astype(np.float32) - bg_color, axis=2)
        alpha = np.where(diff < 38, 0, 255).astype(np.uint8)
        alpha_img = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(1.8))
        garment_img.putalpha(alpha_img)

    if len(u_faces) > 0:
        fx, fy, fw, fh = max(u_faces, key=lambda f: f[2] * f[3])
        target_w = int(fw * 3.3)
        target_h = int(target_w * (garment_img.height / garment_img.width))
        pos_x = int(fx + fw / 2 - target_w / 2)
        pos_y = int(fy + fh * 0.95)
    else:
        target_w = int(person_img.width * 0.62)
        target_h = int(target_w * (garment_img.height / garment_img.width))
        pos_x = int((person_img.width - target_w) / 2)
        pos_y = int(person_img.height * 0.28)

    pos_x = max(0, min(person_img.width - target_w, pos_x))
    pos_y = max(0, min(person_img.height - target_h, pos_y))

    resized_garment = garment_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    mask_canvas = Image.new("L", person_img.size, 0)
    garment_mask = resized_garment.split()[3]
    mask_canvas.paste(garment_mask, (pos_x, pos_y))
    mask_canvas.save(str(final_mask_file), "PNG")

    person_img.paste(resized_garment, (pos_x, pos_y), resized_garment)
    person_img.convert("RGB").save(str(final_file), "PNG")

    print(f"[Virtual Fitting] Garment draping complete: {final_file}")
    return final_file, final_mask_file


# ============================================================
# DETERMINISTIC VIRTUAL TRY-ON (DIRECT FACE OVERLAY)
# ============================================================

def place_user_face_on_clothing(
    person_image,
    garment_image,
    face_target=None,
    output_path=None,
    mask_path=None
):
    """
    Deterministic Virtual Try-On:
    Pins the cropped user profile face directly onto the garment model's face
    at the Admin-marked oval target (or auto-detected position).
    The user's face is rendered ON TOP (front foreground) overlapping the garment.
    Zero external AI model dependencies.
    """
    person_path = Path(person_image)
    garment_path = Path(garment_image)

    if not person_path.exists():
        raise FileNotFoundError(f"User image not found: {person_path}")
    if not garment_path.exists():
        raise FileNotFoundError(f"Garment image not found: {garment_path}")

    if output_path is None:
        output_path = OUTPUT_DIR / "tryon_result.png"
    else:
        output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mask_path is None:
        mask_path = OUTPUT_DIR / "tryon_mask.png"
    else:
        mask_path = Path(mask_path)
    mask_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load garment image
    garment_bgr = cv2.imread(str(garment_path))
    if garment_bgr is None:
        raise ValueError(f"Could not decode garment image: {garment_path}")
    gh, gw = garment_bgr.shape[:2]

    # 2. Load user face
    user_rgba = cv2.imread(str(person_path), cv2.IMREAD_UNCHANGED)
    if user_rgba is None:
        raise ValueError(f"Could not decode user image: {person_path}")

    # If user image does not have an alpha channel, look for a face template or make an oval mask
    if len(user_rgba.shape) < 3 or user_rgba.shape[2] != 4:
        candidate_tmpl = None
        if "user_" in person_path.name:
            import re
            m = re.search(r"user_(\d+)", person_path.name)
            if m:
                u_id = m.group(1)
                tmpl = BASE_DIR / "storage" / "users" / f"user_{u_id}_face_template.png"
                if tmpl.exists():
                    candidate_tmpl = tmpl

        if candidate_tmpl and candidate_tmpl.exists():
            user_rgba = cv2.imread(str(candidate_tmpl), cv2.IMREAD_UNCHANGED)
        else:
            if len(user_rgba.shape) == 2:
                user_bgr = cv2.cvtColor(user_rgba, cv2.COLOR_GRAY2BGR)
            else:
                user_bgr = user_rgba[:, :, :3]
            uh, uw = user_bgr.shape[:2]
            alpha_mask = np.zeros((uh, uw), dtype=np.uint8)
            cv2.ellipse(alpha_mask, (uw // 2, uh // 2), (int(uw * 0.45), int(uh * 0.45)), 0, 0, 360, 255, -1)
            alpha_mask = cv2.GaussianBlur(alpha_mask, (15, 15), 5.0)
            user_rgba = np.dstack([user_bgr, alpha_mask])

    # Crop tightly to non-transparent oval bounds
    alpha_ch = user_rgba[:, :, 3]
    nonzero = np.where(alpha_ch > 10)
    if len(nonzero[0]) > 0 and len(nonzero[1]) > 0:
        ymin, ymax = int(nonzero[0].min()), int(nonzero[0].max())
        xmin, xmax = int(nonzero[1].min()), int(nonzero[1].max())
        user_rgba = user_rgba[ymin:ymax+1, xmin:xmax+1]

    # 3. Parse Admin marked target or fallback
    target = None
    if face_target:
        if isinstance(face_target, str):
            try:
                target = json.loads(face_target)
            except Exception as e:
                print(f"[VTON] Warning: Failed to parse face_target JSON: {e}")
        elif isinstance(face_target, dict):
            target = face_target

    tx, ty, tw, th = None, None, None, None
    angle = 0.0

    if target and isinstance(target, dict):
        angle = float(target.get("angle", 0.0))
        if target.get("norm_w", 0) > 0 and target.get("norm_h", 0) > 0:
            tx = int(target["norm_x"] * gw)
            ty = int(target["norm_y"] * gh)
            tw = int(target["norm_w"] * gw)
            th = int(target["norm_h"] * gh)
        elif "x" in target and "width" in target:
            ref_w = float(target.get("img_w") or gw)
            ref_h = float(target.get("img_h") or gh)
            scale_x = gw / ref_w if ref_w > 0 else 1.0
            scale_y = gh / ref_h if ref_h > 0 else 1.0
            tx = int(target["x"] * scale_x)
            ty = int(target["y"] * scale_y)
            tw = int(target["width"] * scale_x)
            th = int(target["height"] * scale_y)

    # 4. Fallback if Admin has not marked this item yet: Auto-detect model face
    if tx is None or tw is None or tw <= 0 or th <= 0:
        print("[VTON] No Admin face marking found. Auto-detecting model face on garment...")
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        gray = cv2.cvtColor(garment_bgr, cv2.COLOR_BGR2GRAY)
        detected = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
        if len(detected) > 0:
            detected = sorted(detected, key=lambda b: b[2] * b[3], reverse=True)
            fx, fy, fw, fh = detected[0]
            tw = int(fw * 1.15)
            th = int(fh * 1.25)
            tx = max(0, int(fx - (tw - fw) / 2))
            ty = max(0, int(fy - (th - fh) * 0.3))
        else:
            tw = max(50, int(gw * 0.28))
            th = max(60, int(gh * 0.22))
            tx = max(0, int((gw - tw) / 2))
            ty = max(0, int(gh * 0.03))

    tw = max(10, tw)
    th = max(10, th)

    print(f"[VTON Direct Overlay] Placing user face on Admin mark: x={tx}, y={ty}, w={tw}, h={th}, angle={angle} deg")

    # 5. Resize user face to target width and height
    resized_user = cv2.resize(user_rgba, (tw, th), interpolation=cv2.INTER_LANCZOS4)

    # Rotate if tilt angle specified
    if abs(angle) > 0.05:
        rot_mat = cv2.getRotationMatrix2D((tw / 2.0, th / 2.0), -angle, 1.0)
        resized_user = cv2.warpAffine(
            resized_user,
            rot_mat,
            (tw, th),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0, 0)
        )

    # 6. Smooth feathering on alpha channel
    user_bgr = resized_user[:, :, :3]
    user_a = resized_user[:, :, 3].astype(np.float32) / 255.0
    user_a = cv2.GaussianBlur(user_a, (5, 5), 1.2)

    # 7. Front foreground overlap on garment
    dst_x1 = max(0, tx)
    dst_y1 = max(0, ty)
    dst_x2 = min(gw, tx + tw)
    dst_y2 = min(gh, ty + th)

    src_x1 = dst_x1 - tx
    src_y1 = dst_y1 - ty
    src_x2 = src_x1 + (dst_x2 - dst_x1)
    src_y2 = src_y1 + (dst_y2 - dst_y1)

    composite = garment_bgr.copy()
    mask_full = np.zeros((gh, gw), dtype=np.uint8)

    if dst_x2 > dst_x1 and dst_y2 > dst_y1 and src_x2 > src_x1 and src_y2 > src_y1:
        bg_crop = composite[dst_y1:dst_y2, dst_x1:dst_x2].astype(np.float32)
        fg_crop = user_bgr[src_y1:src_y2, src_x1:src_x2].astype(np.float32)
        alpha_crop = user_a[src_y1:src_y2, src_x1:src_x2, np.newaxis]

        # Seamless foreground blend
        blended = (fg_crop * alpha_crop + bg_crop * (1.0 - alpha_crop)).clip(0, 255).astype(np.uint8)
        composite[dst_y1:dst_y2, dst_x1:dst_x2] = blended

        # Record binary mask for downstream consumers
        mask_full[dst_y1:dst_y2, dst_x1:dst_x2] = (user_a[src_y1:src_y2, src_x1:src_x2] * 255).astype(np.uint8)

    # 8. High-Definition scaling for crystal clear zoom and inspection
    if composite.shape[0] < 1080:
        scale_hd = 1080.0 / composite.shape[0]
        hd_w = int(composite.shape[1] * scale_hd)
        composite = cv2.resize(composite, (hd_w, 1080), interpolation=cv2.INTER_LANCZOS4)
        mask_full = cv2.resize(mask_full, (hd_w, 1080), interpolation=cv2.INTER_NEAREST)

    cv2.imwrite(str(output_path), composite)
    cv2.imwrite(str(mask_path), mask_full)

    print(f"[VTON Direct Overlay] Complete! Output saved to: {output_path} (shape: {composite.shape})")
    return output_path, mask_path


# ============================================================
# COMPLETE VIRTUAL TRY-ON
# ============================================================

def generate_virtual_tryon(
    person_image,
    garment_image,
    garment_description="clothing item",
    face_target=None
):
    """
    Virtual Try-on:
    Directly places user's cropped face on top of the Admin-marked face target.
    Zero external AI model dependencies.
    """
    person_image = Path(person_image)
    garment_image = Path(garment_image)

    if not person_image.exists():
        raise FileNotFoundError(f"Person image not found: {person_image}")
    if not garment_image.exists():
        raise FileNotFoundError(f"Garment image not found: {garment_image}")

    final_file = OUTPUT_DIR / "tryon_result.png"
    final_mask_file = OUTPUT_DIR / "tryon_mask.png"

    print("=" * 60)
    print("DIRECT FACE-SWAP VIRTUAL TRY-ON (ON TOP OF ADMIN MARK)")
    print("=" * 60)

    return place_user_face_on_clothing(
        person_image=person_image,
        garment_image=garment_image,
        face_target=face_target,
        output_path=final_file,
        mask_path=final_mask_file
    )
