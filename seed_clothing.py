import sqlite3
from pathlib import Path


# =========================================================
# PROJECT PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = (
    BASE_DIR
    / "storage"
    / "database"
    / "ai_style.db"
)


# =========================================================
# REAL CLOTHING DATA FORMAT
# =========================================================

CLOTHING_DATA = [

    # -----------------------------------------------------
    # WOMEN
    # -----------------------------------------------------

    {
        "outfit_id": "W001",
        "outfit_name": "Women's Casual Dress",
        "category": "Women",
        "clothing_type": "Dress",
        "colour": "Navy Blue",
        "pattern": "Solid",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Hourglass,Pear,Rectangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Balanced,Longer Legs,Longer Torso",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },

    {
        "outfit_id": "W002",
        "outfit_name": "Women's Floral Midi Dress",
        "category": "Women",
        "clothing_type": "Dress",
        "colour": "Pink",
        "pattern": "Floral",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Hourglass,Pear,Rectangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Balanced,Longer Legs",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },

    {
        "outfit_id": "W003",
        "outfit_name": "Women's Black Party Dress",
        "category": "Women",
        "clothing_type": "Party Dress",
        "colour": "Black",
        "pattern": "Solid",
        "style": "Party",
        "occasion": "Party",
        "fit": "Regular",
        "suitable_body_shapes": "Hourglass,Rectangle,Inverted Triangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Balanced,Longer Legs",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },

    {
        "outfit_id": "W004",
        "outfit_name": "Women's White Office Shirt",
        "category": "Women",
        "clothing_type": "Shirt",
        "colour": "White",
        "pattern": "Solid",
        "style": "Formal",
        "occasion": "Office",
        "fit": "Regular",
        "suitable_body_shapes": "Hourglass,Pear,Rectangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Balanced,Longer Torso",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },

    {
        "outfit_id": "W005",
        "outfit_name": "Women's Olive Green Casual Top",
        "category": "Women",
        "clothing_type": "Top",
        "colour": "Olive Green",
        "pattern": "Solid",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Apple,Rectangle,Inverted Triangle",
        "suitable_skin_tones": "Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Balanced,Longer Torso",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },


    # -----------------------------------------------------
    # MEN
    # -----------------------------------------------------

    {
        "outfit_id": "M001",
        "outfit_name": "Men's Navy Formal Shirt",
        "category": "Men",
        "clothing_type": "Shirt",
        "colour": "Navy Blue",
        "pattern": "Solid",
        "style": "Formal",
        "occasion": "Office",
        "fit": "Regular",
        "suitable_body_shapes": "Rectangle,Triangle,Inverted Triangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Balanced,Longer Torso,Longer Legs",
        "min_height_cm": 150,
        "max_height_cm": 195,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },

    {
        "outfit_id": "M002",
        "outfit_name": "Men's Black Casual T-Shirt",
        "category": "Men",
        "clothing_type": "T-Shirt",
        "colour": "Black",
        "pattern": "Solid",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Rectangle,Triangle,Inverted Triangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Balanced,Longer Legs",
        "min_height_cm": 150,
        "max_height_cm": 195,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },

    {
        "outfit_id": "M003",
        "outfit_name": "Men's White Smart Casual Shirt",
        "category": "Men",
        "clothing_type": "Shirt",
        "colour": "White",
        "pattern": "Solid",
        "style": "Smart Casual",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Rectangle,Triangle,Inverted Triangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Balanced",
        "min_height_cm": 150,
        "max_height_cm": 195,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },


    # -----------------------------------------------------
    # KIDS
    # -----------------------------------------------------

    {
        "outfit_id": "K001",
        "outfit_name": "Kids Casual T-Shirt",
        "category": "Kids",
        "clothing_type": "T-Shirt",
        "colour": "Blue",
        "pattern": "Printed",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Not Applicable",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Not Applicable",
        "min_height_cm": 90,
        "max_height_cm": 160,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    },

    {
        "outfit_id": "K002",
        "outfit_name": "Kids Party Dress",
        "category": "Kids",
        "clothing_type": "Dress",
        "colour": "Pink",
        "pattern": "Floral",
        "style": "Party",
        "occasion": "Party",
        "fit": "Regular",
        "suitable_body_shapes": "Not Applicable",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Not Applicable",
        "min_height_cm": 90,
        "max_height_cm": 160,
        "image_path": "",
        "tryon_image_path": "",
        "product_store": "",
        "price": 0
    }
]


# =========================================================
# INSERT / UPDATE CLOTHING
# =========================================================

def save_clothing():

    if not DATABASE_PATH.exists():

        raise FileNotFoundError(
            "Database not found. "
            "Run init_db.py first."
        )

    connection = sqlite3.connect(
        DATABASE_PATH
    )

    try:

        for item in CLOTHING_DATA:

            connection.execute(
                """
                INSERT INTO clothing
                (
                    outfit_id,
                    outfit_name,
                    category,
                    clothing_type,
                    colour,
                    pattern,
                    style,
                    occasion,
                    fit,
                    suitable_body_shapes,
                    suitable_skin_tones,
                    suitable_undertones,
                    suitable_proportion_types,
                    min_height_cm,
                    max_height_cm,
                    image_path,
                    tryon_image_path,
                    product_store,
                    price
                )
                VALUES
                (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(outfit_id)
                DO UPDATE SET
                    outfit_name = excluded.outfit_name,
                    category = excluded.category,
                    clothing_type = excluded.clothing_type,
                    colour = excluded.colour,
                    pattern = excluded.pattern,
                    style = excluded.style,
                    occasion = excluded.occasion,
                    fit = excluded.fit,
                    suitable_body_shapes =
                        excluded.suitable_body_shapes,
                    suitable_skin_tones =
                        excluded.suitable_skin_tones,
                    suitable_undertones =
                        excluded.suitable_undertones,
                    suitable_proportion_types =
                        excluded.suitable_proportion_types,
                    min_height_cm =
                        excluded.min_height_cm,
                    max_height_cm =
                        excluded.max_height_cm,
                    image_path =
                        excluded.image_path,
                    tryon_image_path =
                        excluded.tryon_image_path,
                    product_store =
                        excluded.product_store,
                    price =
                        excluded.price
                """,
                (
                    item["outfit_id"],
                    item["outfit_name"],
                    item["category"],
                    item["clothing_type"],
                    item["colour"],
                    item["pattern"],
                    item["style"],
                    item["occasion"],
                    item["fit"],
                    item["suitable_body_shapes"],
                    item["suitable_skin_tones"],
                    item["suitable_undertones"],
                    item["suitable_proportion_types"],
                    item["min_height_cm"],
                    item["max_height_cm"],
                    item["image_path"],
                    item["tryon_image_path"],
                    item["product_store"],
                    item["price"]
                )
            )

        connection.commit()

    finally:

        connection.close()


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("CLOTHING DATABASE SETUP")
    print("=" * 60)

    save_clothing()

    print(
        f"{len(CLOTHING_DATA)} clothing records "
        "inserted/updated successfully."
    )

    print(
        "Clothing database is ready."
    )

    print("=" * 60)