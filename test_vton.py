from pathlib import Path
from shutil import copy2

from gradio_client import Client, file


# ---------------------------------------------------------
# PROJECT PATHS
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

PERSON_IMAGE = BASE_DIR / "storage" / "temp" / "test_person.jpeg"
GARMENT_IMAGE = BASE_DIR / "storage" / "clothing" / "test_garment.jpeg"

OUTPUT_DIR = BASE_DIR / "storage" / "temp" / "vton_test"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# CHECK FILES
# ---------------------------------------------------------

if not PERSON_IMAGE.exists():
    raise FileNotFoundError(
        f"Person image not found:\n{PERSON_IMAGE}"
    )

if not GARMENT_IMAGE.exists():
    raise FileNotFoundError(
        f"Garment image not found:\n{GARMENT_IMAGE}"
    )


print("========================================")
print("IDM-VTON API TEST")
print("========================================")

print(f"Person image : {PERSON_IMAGE}")
print(f"Garment image: {GARMENT_IMAGE}")

print("\nConnecting to IDM-VTON...")

client = Client("yisol/IDM-VTON")

print("Connected successfully.")

print("\nGenerating virtual try-on...")
print("Please wait...\n")


# ---------------------------------------------------------
# IDM-VTON API
# ---------------------------------------------------------

result = client.predict(
    {
        "background": file(str(PERSON_IMAGE)),
        "layers": [],
        "composite": None
    },
    file(str(GARMENT_IMAGE)),
    "Short sleeve blue top",
    True,
    True,
    30,
    42,
    api_name="/tryon"
)


# ---------------------------------------------------------
# RESULTS
# ---------------------------------------------------------

output_image = result[0]
masked_image = result[1]

print("========================================")
print("VIRTUAL TRY-ON COMPLETED")
print("========================================")

print("Generated output :", output_image)
print("Masked image     :", masked_image)


# ---------------------------------------------------------
# SAVE RESULTS
# ---------------------------------------------------------

output_file = OUTPUT_DIR / "test_result.png"
masked_file = OUTPUT_DIR / "test_mask.png"

copy2(output_image, output_file)
copy2(masked_image, masked_file)

print("\nSaved files:")

print(f"Result: {output_file}")
print(f"Mask  : {masked_file}")

print("\nSUCCESS! IDM-VTON API is working.")