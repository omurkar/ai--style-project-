from pathlib import Path

import cv2
import mediapipe as mp


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

TEMP_DIR = BASE_DIR / "storage" / "temp"
TEMP_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# MEDIAPIPE SETUP
# =========================================================

mp_pose = mp.solutions.pose


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def get_landmark_point(landmarks, landmark_name, image_width, image_height):
    """
    Convert a MediaPipe landmark into pixel coordinates.
    """

    landmark = landmarks[landmark_name]

    x = int(landmark.x * image_width)
    y = int(landmark.y * image_height)

    return x, y


def get_landmark_visibility(landmarks, landmark_name):
    """
    Return MediaPipe landmark visibility.
    """

    return float(
        landmarks[landmark_name].visibility
    )


def get_segmentation_width(mask, y, center_x):
    """
    Estimate body width from the segmentation mask
    around a particular vertical position.

    Only the connected body region containing the
    body centre is considered.
    """

    height, width = mask.shape

    y = max(0, min(height - 1, int(y)))

    threshold = 0.5

    row = mask[y] > threshold

    if not row.any():
        return 0

    center_x = max(0, min(width - 1, int(center_x)))

    # If centre is not inside the detected body,
    # search nearby pixels.
    if not row[center_x]:

        found_center = None

        for distance in range(1, min(80, width)):
            left = center_x - distance
            right = center_x + distance

            if left >= 0 and row[left]:
                found_center = left
                break

            if right < width and row[right]:
                found_center = right
                break

        if found_center is None:
            return 0

        center_x = found_center

    # Move left until body ends
    left = center_x

    while left > 0 and row[left - 1]:
        left -= 1

    # Move right until body ends
    right = center_x

    while right < width - 1 and row[right + 1]:
        right += 1

    return right - left + 1


def get_average_segmentation_width(
    mask,
    y,
    center_x,
    offset=10
):
    """
    Average body width across a few nearby rows.
    This reduces noise from clothing and segmentation.
    """

    widths = []

    for delta in range(-offset, offset + 1, 5):

        current_y = int(y + delta)

        width = get_segmentation_width(
            mask,
            current_y,
            center_x
        )

        if width > 0:
            widths.append(width)

    if not widths:
        return 0

    return sum(widths) / len(widths)


# =========================================================
# BODY SHAPE CLASSIFICATION
# =========================================================

def classify_body_shape(
    shoulder_width,
    waist_width,
    hip_width
):
    """
    Estimate adult body shape from shoulder,
    waist and hip proportions.

    This is an image-based estimate only.
    It is not a physical measurement.
    """

    if (
        shoulder_width <= 0
        or waist_width <= 0
        or hip_width <= 0
    ):
        return "Not Determined"

    # -----------------------------------------------------
    # Normalize waist relative to shoulders and hips
    # -----------------------------------------------------

    shoulder_hip_average = (
        shoulder_width + hip_width
    ) / 2

    waist_ratio = (
        waist_width / shoulder_hip_average
    )

    shoulder_hip_ratio = (
        shoulder_width / hip_width
    )

    # -----------------------------------------------------
    # HOURGLASS
    #
    # Shoulders and hips are reasonably similar,
    # while waist is noticeably narrower.
    # -----------------------------------------------------

    if (
        0.90 <= shoulder_hip_ratio <= 1.10
        and waist_ratio <= 0.78
    ):
        return "Hourglass"

    # -----------------------------------------------------
    # PEAR
    #
    # Hips noticeably wider than shoulders
    # and waist is narrower than hips.
    # -----------------------------------------------------

    if (
        hip_width >= shoulder_width * 1.08
        and waist_width <= hip_width * 0.88
    ):
        return "Pear"

    # -----------------------------------------------------
    # INVERTED TRIANGLE
    #
    # Shoulders noticeably wider than hips
    # and waist is narrower than shoulders.
    # -----------------------------------------------------

    if (
        shoulder_width >= hip_width * 1.08
        and waist_width <= shoulder_width * 0.88
    ):
        return "Inverted Triangle"

    # -----------------------------------------------------
    # APPLE
    #
    # Waist is comparatively wider and there is
    # less waist definition.
    # -----------------------------------------------------

    if (
        waist_width >= shoulder_width * 0.92
        and waist_width >= hip_width * 0.92
    ):
        return "Apple"

    # -----------------------------------------------------
    # RECTANGLE
    #
    # Shoulders, waist and hips are relatively similar.
    # -----------------------------------------------------

    return "Rectangle"


# =========================================================
# BODY PROPORTION CLASSIFICATION
# =========================================================

def classify_body_proportions(
    shoulder_width,
    waist_width,
    hip_width
):
    """
    Estimate the general width relationship.
    """

    if (
        shoulder_width <= 0
        or hip_width <= 0
    ):
        return "Not Determined"

    if shoulder_width >= hip_width * 1.08:
        return "Wider Shoulders"

    if hip_width >= shoulder_width * 1.08:
        return "Wider Hips"

    return "Balanced"


# =========================================================
# LEG PROPORTION
# =========================================================

def classify_leg_proportion(
    hip_y,
    ankle_y,
    image_height
):
    """
    Estimate visible leg-to-body proportion.

    This does NOT calculate actual leg length.
    """

    if image_height <= 0:
        return "Not Determined"

    vertical_distance = abs(
        ankle_y - hip_y
    )

    normalized_distance = (
        vertical_distance / image_height
    )

    if normalized_distance >= 0.43:
        return "Longer Legs"

    if normalized_distance <= 0.32:
        return "Shorter Legs"

    return "Balanced"


# =========================================================
# MAIN BODY ANALYSIS FUNCTION
# =========================================================

def analyze_body(image_path):
    """
    Analyze a person's photograph using MediaPipe Pose.

    Uses:
    - Pose landmarks
    - Body segmentation
    - Shoulder width
    - Waist width estimate
    - Hip width
    - Leg proportion

    IMPORTANT:
    This produces clothing-related estimates only.
    It does NOT calculate exact height from a photograph.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found:\n{image_path}"
        )

    # -----------------------------------------------------
    # READ IMAGE
    # -----------------------------------------------------

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError(
            "The selected file could not be read as an image."
        )

    image_height, image_width = image.shape[:2]

    image_rgb = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2RGB
    )

    # -----------------------------------------------------
    # MEDIAPIPE POSE
    # -----------------------------------------------------

    with mp_pose.Pose(
        static_image_mode=True,
        model_complexity=1,
        enable_segmentation=True,
        smooth_segmentation=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:

        results = pose.process(image_rgb)

    # -----------------------------------------------------
    # CHECK LANDMARKS
    # -----------------------------------------------------

    if not results.pose_landmarks:

        return {
            "success": False,
            "body_shape": "Not Determined",
            "body_proportions": "Not Determined",
            "leg_proportion": "Not Determined",
            "shoulder_width_ratio": 0,
            "hip_width_ratio": 0,
            "waist_width_ratio": 0,
            "message": (
                "No clear human body landmarks were detected. "
                "Please upload a clear full-body photograph."
            )
        }

    landmarks = results.pose_landmarks.landmark

    # -----------------------------------------------------
    # IMPORTANT LANDMARKS
    # -----------------------------------------------------

    left_shoulder = mp_pose.PoseLandmark.LEFT_SHOULDER
    right_shoulder = mp_pose.PoseLandmark.RIGHT_SHOULDER

    left_hip = mp_pose.PoseLandmark.LEFT_HIP
    right_hip = mp_pose.PoseLandmark.RIGHT_HIP

    left_ankle = mp_pose.PoseLandmark.LEFT_ANKLE
    right_ankle = mp_pose.PoseLandmark.RIGHT_ANKLE

    # -----------------------------------------------------
    # VISIBILITY CHECK
    # -----------------------------------------------------

    important_landmarks = [
        left_shoulder,
        right_shoulder,
        left_hip,
        right_hip,
        left_ankle,
        right_ankle
    ]

    visibility_values = [
        get_landmark_visibility(
            landmarks,
            landmark
        )
        for landmark in important_landmarks
    ]

    average_visibility = (
        sum(visibility_values)
        / len(visibility_values)
    )

    # -----------------------------------------------------
    # LANDMARK PIXEL POSITIONS
    # -----------------------------------------------------

    left_shoulder_x, left_shoulder_y = get_landmark_point(
        landmarks,
        left_shoulder,
        image_width,
        image_height
    )

    right_shoulder_x, right_shoulder_y = get_landmark_point(
        landmarks,
        right_shoulder,
        image_width,
        image_height
    )

    left_hip_x, left_hip_y = get_landmark_point(
        landmarks,
        left_hip,
        image_width,
        image_height
    )

    right_hip_x, right_hip_y = get_landmark_point(
        landmarks,
        right_hip,
        image_width,
        image_height
    )

    left_ankle_x, left_ankle_y = get_landmark_point(
        landmarks,
        left_ankle,
        image_width,
        image_height
    )

    right_ankle_x, right_ankle_y = get_landmark_point(
        landmarks,
        right_ankle,
        image_width,
        image_height
    )

    # -----------------------------------------------------
    # SHOULDER WIDTH
    # -----------------------------------------------------

    shoulder_width = abs(
        left_shoulder_x - right_shoulder_x
    )

    # -----------------------------------------------------
    # HIP WIDTH
    # -----------------------------------------------------

    hip_width = abs(
        left_hip_x - right_hip_x
    )

    # -----------------------------------------------------
    # BODY CENTRE
    # -----------------------------------------------------

    shoulder_center_x = (
        left_shoulder_x + right_shoulder_x
    ) / 2

    hip_center_x = (
        left_hip_x + right_hip_x
    ) / 2

    body_center_x = (
        shoulder_center_x + hip_center_x
    ) / 2

    # -----------------------------------------------------
    # WAIST POSITION
    #
    # Approx. 60% down from shoulders to hips.
    # -----------------------------------------------------

    shoulder_center_y = (
        left_shoulder_y + right_shoulder_y
    ) / 2

    hip_center_y = (
        left_hip_y + right_hip_y
    ) / 2

    waist_y = (
        shoulder_center_y
        + 0.60 * (
            hip_center_y - shoulder_center_y
        )
    )

    # -----------------------------------------------------
    # SEGMENTATION MASK
    # -----------------------------------------------------

    waist_width = 0

    if results.segmentation_mask is not None:

        segmentation_mask = (
            results.segmentation_mask
        )

        waist_width = get_average_segmentation_width(
            segmentation_mask,
            waist_y,
            body_center_x,
            offset=12
        )

    # -----------------------------------------------------
    # FALLBACK WAIST ESTIMATE
    #
    # If segmentation cannot determine the waist,
    # use a conservative estimate instead of crashing.
    # -----------------------------------------------------

    if waist_width <= 0:

        waist_width = (
            shoulder_width + hip_width
        ) / 2 * 0.85

    # -----------------------------------------------------
    # NORMALIZED WIDTH VALUES
    # -----------------------------------------------------

    shoulder_width_ratio = (
        shoulder_width / image_width
    )

    hip_width_ratio = (
        hip_width / image_width
    )

    waist_width_ratio = (
        waist_width / image_width
    )

    # -----------------------------------------------------
    # BODY SHAPE
    # -----------------------------------------------------

    body_shape = classify_body_shape(
        shoulder_width,
        waist_width,
        hip_width
    )

    # -----------------------------------------------------
    # BODY PROPORTIONS
    # -----------------------------------------------------

    body_proportions = classify_body_proportions(
        shoulder_width,
        waist_width,
        hip_width
    )

    # -----------------------------------------------------
    # LEG PROPORTION
    # -----------------------------------------------------

    average_hip_y = (
        left_hip_y + right_hip_y
    ) / 2

    average_ankle_y = (
        left_ankle_y + right_ankle_y
    ) / 2

    leg_proportion = classify_leg_proportion(
        average_hip_y,
        average_ankle_y,
        image_height
    )

    # -----------------------------------------------------
    # QUALITY MESSAGE
    # -----------------------------------------------------

    if average_visibility < 0.55:

        message = (
            "Body landmarks were detected with limited "
            "visibility. Results may be less reliable."
        )

    elif results.segmentation_mask is None:

        message = (
            "Body landmarks were detected successfully. "
            "Body-shape estimates are based mainly on pose "
            "landmarks."
        )

    else:

        message = (
            "Body landmarks and body silhouette were "
            "analysed successfully."
        )

    # -----------------------------------------------------
    # FINAL RESULT
    # -----------------------------------------------------

    return {
        "success": True,

        "body_shape": body_shape,

        "body_proportions": body_proportions,

        "leg_proportion": leg_proportion,

        "shoulder_width_ratio": round(
            shoulder_width_ratio,
            3
        ),

        "hip_width_ratio": round(
            hip_width_ratio,
            3
        ),

        "waist_width_ratio": round(
            waist_width_ratio,
            3
        ),

        "landmark_visibility": round(
            average_visibility,
            3
        ),

        "message": message
    }


# =========================================================
# SIMPLE TEST
# =========================================================

if __name__ == "__main__":

    test_image = (
        TEMP_DIR / "test_person.jpeg"
    )

    print("=" * 60)
    print("AI BODY ANALYSIS TEST")
    print("=" * 60)

    print(
        f"Testing image: {test_image}"
    )

    try:

        result = analyze_body(
            test_image
        )

        print("\nAnalysis Result:")
        print("-" * 60)

        for key, value in result.items():

            print(
                f"{key}: {value}"
            )

    except Exception as error:

        print("\nERROR:")
        print(error)