from pathlib import Path

import cv2
import numpy as np
import mediapipe as mp


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

TEMP_DIR = (
    BASE_DIR
    / "storage"
    / "temp"
)

TEMP_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# MEDIAPIPE FACE DETECTION
# =========================================================

mp_face_detection = mp.solutions.face_detection


# =========================================================
# SKIN TONE CATEGORIES
# =========================================================

SKIN_TONES = [
    "Very Fair",
    "Fair",
    "Light",
    "Medium",
    "Tan",
    "Deep",
    "Dark"
]


# =========================================================
# CHECK IMAGE
# =========================================================

def load_image(image_path):

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    image = cv2.imread(
        str(image_path)
    )

    if image is None:
        raise ValueError(
            "The selected file could not be read as an image."
        )

    return image


# =========================================================
# FACE DETECTION
# =========================================================

def detect_face(image):

    image_rgb = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    with mp_face_detection.FaceDetection(
        model_selection=1,
        min_detection_confidence=0.5
    ) as detector:

        results = detector.process(
            image_rgb
        )

    if not results.detections:
        return None

    # Select the largest detected face
    image_height, image_width = image.shape[:2]

    best_detection = None
    best_area = 0

    for detection in results.detections:

        box = detection.location_data.relative_bounding_box

        x = max(
            0,
            int(box.xmin * image_width)
        )

        y = max(
            0,
            int(box.ymin * image_height)
        )

        width = int(
            box.width * image_width
        )

        height = int(
            box.height * image_height
        )

        width = min(
            width,
            image_width - x
        )

        height = min(
            height,
            image_height - y
        )

        area = width * height

        if area > best_area:

            best_area = area

            best_detection = (
                x,
                y,
                width,
                height
            )

    return best_detection


# =========================================================
# EXTRACT SKIN REGION
# =========================================================

def extract_skin_region(
    image,
    face_box
):

    x, y, width, height = face_box

    if width <= 0 or height <= 0:
        return None

    # -----------------------------------------------------
    # We avoid the outer edges of the face.
    # This reduces hair/background contamination.
    # -----------------------------------------------------

    left = int(
        x + width * 0.25
    )

    right = int(
        x + width * 0.75
    )

    top = int(
        y + height * 0.25
    )

    bottom = int(
        y + height * 0.70
    )

    left = max(
        0,
        left
    )

    top = max(
        0,
        top
    )

    right = min(
        image.shape[1],
        right
    )

    bottom = min(
        image.shape[0],
        bottom
    )

    if right <= left or bottom <= top:
        return None

    region = image[
        top:bottom,
        left:right
    ]

    if region.size == 0:
        return None

    return region


# =========================================================
# CREATE SKIN PIXEL MASK
# =========================================================

def get_skin_pixels(
    region
):

    # Convert BGR → HSV
    hsv = cv2.cvtColor(
        region,
        cv2.COLOR_BGR2HSV
    )

    # Convert BGR → YCrCb
    ycrcb = cv2.cvtColor(
        region,
        cv2.COLOR_BGR2YCrCb
    )

    # -----------------------------------------------------
    # HSV values
    # -----------------------------------------------------

    h = hsv[:, :, 0]
    s = hsv[:, :, 1]
    v = hsv[:, :, 2]

    # -----------------------------------------------------
    # YCrCb values
    # -----------------------------------------------------

    cr = ycrcb[:, :, 1]
    cb = ycrcb[:, :, 2]

    # -----------------------------------------------------
    # Skin detection rules
    #
    # These are intentionally broad because skin tones
    # vary across people and lighting conditions.
    # -----------------------------------------------------

    mask_hsv = (
        (h >= 0)
        &
        (h <= 35)
        &
        (s >= 15)
        &
        (s <= 220)
        &
        (v >= 35)
    )

    mask_ycrcb = (
        (cr >= 125)
        &
        (cr <= 185)
        &
        (cb >= 70)
        &
        (cb <= 140)
    )

    # Accept pixels that satisfy either reasonable
    # skin condition.
    skin_mask = (
        mask_hsv
        |
        mask_ycrcb
    )

    pixels = region[
        skin_mask
    ]

    if len(pixels) == 0:
        return None

    return pixels


# =========================================================
# CALCULATE ROBUST SKIN COLOUR
# =========================================================

def calculate_skin_colour(
    skin_pixels
):

    if skin_pixels is None:
        return None

    if len(skin_pixels) < 20:
        return None

    # -----------------------------------------------------
    # Remove extreme dark/bright pixels.
    # This reduces influence from shadows and highlights.
    # -----------------------------------------------------

    rgb_pixels = cv2.cvtColor(
        skin_pixels.reshape(
            -1,
            1,
            3
        ),
        cv2.COLOR_BGR2RGB
    ).reshape(
        -1,
        3
    )

    brightness = (
        0.299 * rgb_pixels[:, 0]
        +
        0.587 * rgb_pixels[:, 1]
        +
        0.114 * rgb_pixels[:, 2]
    )

    low = np.percentile(
        brightness,
        10
    )

    high = np.percentile(
        brightness,
        90
    )

    valid = (
        (brightness >= low)
        &
        (brightness <= high)
    )

    filtered = rgb_pixels[
        valid
    ]

    if len(filtered) < 10:
        filtered = rgb_pixels

    median_rgb = np.median(
        filtered,
        axis=0
    )

    return (
        float(median_rgb[0]),
        float(median_rgb[1]),
        float(median_rgb[2])
    )


# =========================================================
# SKIN TONE CLASSIFICATION
# =========================================================

def classify_skin_tone(
    rgb
):

    if rgb is None:
        return "Not Determined"

    r, g, b = rgb

    # -----------------------------------------------------
    # Perceived brightness
    # -----------------------------------------------------

    brightness = (
        0.299 * r
        +
        0.587 * g
        +
        0.114 * b
    )

    # -----------------------------------------------------
    # Practical project categories.
    #
    # These are estimates, not medical/clinical
    # classifications.
    # -----------------------------------------------------

    if brightness >= 215:
        return "Very Fair"

    if brightness >= 190:
        return "Fair"

    if brightness >= 165:
        return "Light"

    if brightness >= 135:
        return "Medium"

    if brightness >= 105:
        return "Tan"

    if brightness >= 75:
        return "Deep"

    return "Dark"


# =========================================================
# UNDERTONE CLASSIFICATION
# =========================================================

def classify_undertone(
    rgb
):

    if rgb is None:
        return "Not Determined"

    r, g, b = rgb

    # -----------------------------------------------------
    # Warm / cool estimation based on relative
    # red/green/blue balance.
    # -----------------------------------------------------

    red_difference = r - b
    yellow_difference = (
        (r + g) / 2
    ) - b

    # Warm
    if (
        red_difference >= 18
        and yellow_difference >= 12
    ):
        return "Warm"

    # Cool
    if (
        b - r >= 8
    ):
        return "Cool"

    # Otherwise
    return "Neutral"


# =========================================================
# CONFIDENCE ESTIMATION
# =========================================================

def calculate_confidence(
    skin_pixels,
    face_box
):

    if skin_pixels is None:
        return 0

    pixel_count = len(
        skin_pixels
    )

    x, y, width, height = face_box

    face_area = (
        width * height
    )

    if face_area <= 0:
        return 0

    # Number of detected skin pixels
    # compared with face area.
    coverage = (
        pixel_count
        /
        face_area
    )

    # Practical confidence score.
    if coverage >= 0.25:
        confidence = 0.90

    elif coverage >= 0.15:
        confidence = 0.80

    elif coverage >= 0.08:
        confidence = 0.70

    elif coverage >= 0.04:
        confidence = 0.60

    else:
        confidence = 0.45

    return round(
        confidence,
        2
    )


# =========================================================
# MAIN SKIN TONE ANALYSIS
# =========================================================

def analyze_skin_tone(
    image_path
):

    image_path = Path(
        image_path
    )

    image = load_image(
        image_path
    )

    # -----------------------------------------------------
    # Detect face
    # -----------------------------------------------------

    face_box = detect_face(
        image
    )

    if face_box is None:

        return {
            "success": False,
            "skin_tone": "Not Determined",
            "undertone": "Not Determined",
            "confidence": 0,
            "message": (
                "No clear face was detected. "
                "Please upload a clear photo with "
                "your face visible."
            )
        }

    # -----------------------------------------------------
    # Extract probable skin area
    # -----------------------------------------------------

    skin_region = extract_skin_region(
        image,
        face_box
    )

    if skin_region is None:

        return {
            "success": False,
            "skin_tone": "Not Determined",
            "undertone": "Not Determined",
            "confidence": 0,
            "message": (
                "A suitable skin region could not "
                "be extracted from the face."
            )
        }

    # -----------------------------------------------------
    # Extract skin pixels
    # -----------------------------------------------------

    skin_pixels = get_skin_pixels(
        skin_region
    )

    if skin_pixels is None:

        return {
            "success": False,
            "skin_tone": "Not Determined",
            "undertone": "Not Determined",
            "confidence": 0,
            "message": (
                "Skin pixels could not be detected "
                "reliably. Try a clearer photo "
                "with better lighting."
            )
        }

    # -----------------------------------------------------
    # Calculate representative RGB
    # -----------------------------------------------------

    rgb = calculate_skin_colour(
        skin_pixels
    )

    if rgb is None:

        return {
            "success": False,
            "skin_tone": "Not Determined",
            "undertone": "Not Determined",
            "confidence": 0,
            "message": (
                "Not enough reliable skin pixels "
                "were detected."
            )
        }

    # -----------------------------------------------------
    # Classify
    # -----------------------------------------------------

    skin_tone = classify_skin_tone(
        rgb
    )

    undertone = classify_undertone(
        rgb
    )

    confidence = calculate_confidence(
        skin_pixels,
        face_box
    )

    # -----------------------------------------------------
    # Result message
    # -----------------------------------------------------

    if confidence >= 0.80:

        message = (
            "Skin tone and undertone were "
            "estimated successfully. "
            "Lighting can affect the result, "
            "so please verify the detected values."
        )

    else:

        message = (
            "Skin tone was estimated with limited "
            "confidence. Please verify the result "
            "under good lighting."
        )

    return {
        "success": True,
        "skin_tone": skin_tone,
        "undertone": undertone,
        "confidence": confidence,
        "rgb": tuple(
            round(value, 2)
            for value in rgb
        ),
        "face_box": face_box,
        "skin_pixel_count": int(
            len(skin_pixels)
        ),
        "message": message
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    test_image = (
        TEMP_DIR
        / "test_person.jpeg"
    )

    print("=" * 60)
    print("AI SKIN TONE ANALYSIS TEST")
    print("=" * 60)

    print(
        f"Testing image: {test_image}"
    )

    try:

        result = analyze_skin_tone(
            test_image
        )

        print("\nAnalysis Result:")
        print("-" * 60)

        for key, value in result.items():

            print(
                f"{key}: {value}"
            )

        print("-" * 60)

        if result["success"]:

            print(
                "\nSKIN TONE:",
                result["skin_tone"]
            )

            print(
                "UNDERTONE:",
                result["undertone"]
            )

            print(
                "CONFIDENCE:",
                result["confidence"]
            )

        else:

            print(
                "\nSkin tone analysis "
                "could not be completed."
            )

    except Exception as error:

        print("\nERROR:")
        print(error)