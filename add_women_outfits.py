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
# WOMEN OUTFIT DATA
#
# W001-W007 already exist.
# This file adds ONLY W008-W025.
#
# These are academic/demo catalogue records.
# Real verified product information can be added later.
# ============================================================

WOMEN_OUTFITS = [

    # ========================================================
    # TOPS
    # ========================================================

    {
        "outfit_id": "W008",
        "outfit_name": "Ivory Relaxed Everyday Top",
        "category": "Women",
        "clothing_type": "Top",
        "colour": "Ivory",
        "pattern": "Solid",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Relaxed",
        "suitable_body_shapes": "Pear,Apple,Rectangle,Hourglass",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1299,
        "age_group": "Adults",
        "material": "Cotton",
        "season": "All Season",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A simple ivory relaxed-fit top designed for comfortable everyday styling."
    },

    {
        "outfit_id": "W009",
        "outfit_name": "Sage Green Ribbed Top",
        "category": "Women",
        "clothing_type": "Top",
        "colour": "Sage Green",
        "pattern": "Solid",
        "style": "Minimal",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Hourglass,Pear,Rectangle",
        "suitable_skin_tones": "Fair,Light,Medium,Tan,Deep",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1399,
        "age_group": "Adults",
        "material": "Ribbed Cotton",
        "season": "Spring,Summer,Autumn",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A minimal sage green ribbed top suitable for casual everyday outfits."
    },

    {
        "outfit_id": "W010",
        "outfit_name": "Maroon V-Neck Casual Top",
        "category": "Women",
        "clothing_type": "Top",
        "colour": "Maroon",
        "pattern": "Solid",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Regular",
        "suitable_body_shapes": "Apple,Rectangle,Inverted Triangle,Hourglass",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Neutral,Cool",
        "suitable_proportion_types": "Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1499,
        "age_group": "Adults",
        "material": "Cotton Blend",
        "season": "All Season",
        "available_sizes": "S,M,L,XL,XXL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A maroon V-neck top designed for simple casual styling."
    },


    # ========================================================
    # SHIRTS / BLOUSES
    # ========================================================

    {
        "outfit_id": "W011",
        "outfit_name": "Sky Blue Office Shirt",
        "category": "Women",
        "clothing_type": "Shirt",
        "colour": "Sky Blue",
        "pattern": "Solid",
        "style": "Formal",
        "occasion": "Office",
        "fit": "Regular",
        "suitable_body_shapes": "Apple,Rectangle,Inverted Triangle,Hourglass",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1799,
        "age_group": "Adults",
        "material": "Cotton",
        "season": "All Season",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A clean sky blue formal shirt suitable for office and professional styling."
    },

    {
        "outfit_id": "W012",
        "outfit_name": "White Classic Formal Shirt",
        "category": "Women",
        "clothing_type": "Shirt",
        "colour": "White",
        "pattern": "Solid",
        "style": "Formal",
        "occasion": "Office",
        "fit": "Regular",
        "suitable_body_shapes": "Pear,Apple,Rectangle,Hourglass,Inverted Triangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Wider Hips,Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1699,
        "age_group": "Adults",
        "material": "Cotton",
        "season": "All Season",
        "available_sizes": "XS,S,M,L,XL,XXL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A versatile white formal shirt suitable for professional and smart-casual looks."
    },

    {
        "outfit_id": "W013",
        "outfit_name": "Dusty Rose Blouse",
        "category": "Women",
        "clothing_type": "Blouse",
        "colour": "Dusty Rose",
        "pattern": "Solid",
        "style": "Elegant",
        "occasion": "Party",
        "fit": "Regular",
        "suitable_body_shapes": "Pear,Hourglass,Rectangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 178,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1999,
        "age_group": "Adults",
        "material": "Georgette",
        "season": "Spring,Autumn,Winter",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "An elegant dusty rose blouse designed for semi-formal and party styling."
    },


    # ========================================================
    # DRESSES
    # ========================================================

    {
        "outfit_id": "W014",
        "outfit_name": "Navy A-Line Midi Dress",
        "category": "Women",
        "clothing_type": "Dress",
        "colour": "Navy Blue",
        "pattern": "Solid",
        "style": "Elegant",
        "occasion": "Party",
        "fit": "A-Line",
        "suitable_body_shapes": "Pear,Apple,Rectangle,Inverted Triangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Wider Hips,Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 2799,
        "age_group": "Adults",
        "material": "Crepe",
        "season": "All Season",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A navy A-line midi dress designed to create a balanced and elegant silhouette."
    },

    {
        "outfit_id": "W015",
        "outfit_name": "Emerald Wrap Dress",
        "category": "Women",
        "clothing_type": "Dress",
        "colour": "Emerald Green",
        "pattern": "Solid",
        "style": "Elegant",
        "occasion": "Party",
        "fit": "Wrap",
        "suitable_body_shapes": "Apple,Rectangle,Pear,Hourglass",
        "suitable_skin_tones": "Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 2999,
        "age_group": "Adults",
        "material": "Polyester Crepe",
        "season": "All Season",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "An emerald wrap dress with a defined waist suitable for party and evening occasions."
    },

    {
        "outfit_id": "W016",
        "outfit_name": "Black Straight Midi Dress",
        "category": "Women",
        "clothing_type": "Dress",
        "colour": "Black",
        "pattern": "Solid",
        "style": "Minimal",
        "occasion": "Office",
        "fit": "Straight",
        "suitable_body_shapes": "Apple,Rectangle,Inverted Triangle,Hourglass",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 2499,
        "age_group": "Adults",
        "material": "Crepe",
        "season": "All Season",
        "available_sizes": "XS,S,M,L,XL,XXL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A minimal black straight-fit midi dress suitable for office and semi-formal occasions."
    },


    # ========================================================
    # TROUSERS / JEANS
    # ========================================================

    {
        "outfit_id": "W017",
        "outfit_name": "High-Waist Beige Trousers",
        "category": "Women",
        "clothing_type": "Trousers",
        "colour": "Beige",
        "pattern": "Solid",
        "style": "Smart Casual",
        "occasion": "Office",
        "fit": "Straight",
        "suitable_body_shapes": "Pear,Hourglass,Rectangle,Apple",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1899,
        "age_group": "Adults",
        "material": "Cotton Blend",
        "season": "All Season",
        "available_sizes": "26,28,30,32,34,36",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "High-waist beige trousers suitable for office and smart-casual outfits."
    },

    {
        "outfit_id": "W018",
        "outfit_name": "Dark Blue Straight Jeans",
        "category": "Women",
        "clothing_type": "Jeans",
        "colour": "Dark Blue",
        "pattern": "Solid",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Straight",
        "suitable_body_shapes": "Pear,Apple,Rectangle,Hourglass,Inverted Triangle",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Wider Hips,Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1999,
        "age_group": "Adults",
        "material": "Denim",
        "season": "All Season",
        "available_sizes": "26,28,30,32,34,36",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "Dark blue straight-fit jeans designed for versatile everyday styling."
    },

    {
        "outfit_id": "W019",
        "outfit_name": "Black Wide-Leg Trousers",
        "category": "Women",
        "clothing_type": "Trousers",
        "colour": "Black",
        "pattern": "Solid",
        "style": "Formal",
        "occasion": "Office",
        "fit": "Wide Leg",
        "suitable_body_shapes": "Inverted Triangle,Apple,Rectangle,Hourglass",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 2199,
        "age_group": "Adults",
        "material": "Polyester Blend",
        "season": "All Season",
        "available_sizes": "26,28,30,32,34,36",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "Black wide-leg trousers designed for balanced office and formal styling."
    },


    # ========================================================
    # SKIRTS
    # ========================================================

    {
        "outfit_id": "W020",
        "outfit_name": "Olive A-Line Midi Skirt",
        "category": "Women",
        "clothing_type": "Skirt",
        "colour": "Olive Green",
        "pattern": "Solid",
        "style": "Smart Casual",
        "occasion": "Casual",
        "fit": "A-Line",
        "suitable_body_shapes": "Pear,Hourglass,Rectangle,Apple",
        "suitable_skin_tones": "Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1799,
        "age_group": "Adults",
        "material": "Cotton",
        "season": "Spring,Summer,Autumn",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "An olive A-line midi skirt suitable for casual and smart-casual looks."
    },

    {
        "outfit_id": "W021",
        "outfit_name": "Burgundy Pleated Midi Skirt",
        "category": "Women",
        "clothing_type": "Skirt",
        "colour": "Burgundy",
        "pattern": "Pleated",
        "style": "Elegant",
        "occasion": "Party",
        "fit": "Flowy",
        "suitable_body_shapes": "Apple,Inverted Triangle,Rectangle,Hourglass",
        "suitable_skin_tones": "Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 2099,
        "age_group": "Adults",
        "material": "Polyester",
        "season": "Autumn,Winter",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A burgundy pleated midi skirt designed to add movement and volume to an outfit."
    },


    # ========================================================
    # ETHNIC / KURTIS
    # ========================================================

    {
        "outfit_id": "W022",
        "outfit_name": "Mustard Straight Kurti",
        "category": "Women",
        "clothing_type": "Kurti",
        "colour": "Mustard Yellow",
        "pattern": "Printed",
        "style": "Ethnic",
        "occasion": "Festive",
        "fit": "Straight",
        "suitable_body_shapes": "Apple,Rectangle,Pear,Hourglass",
        "suitable_skin_tones": "Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 1599,
        "age_group": "Adults",
        "material": "Cotton",
        "season": "Spring,Summer,Autumn",
        "available_sizes": "S,M,L,XL,XXL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A mustard printed straight kurti suitable for festive and everyday ethnic styling."
    },

    {
        "outfit_id": "W023",
        "outfit_name": "Teal Anarkali Kurti",
        "category": "Women",
        "clothing_type": "Kurti",
        "colour": "Teal",
        "pattern": "Printed",
        "style": "Ethnic",
        "occasion": "Festive",
        "fit": "Anarkali",
        "suitable_body_shapes": "Apple,Rectangle,Inverted Triangle,Pear",
        "suitable_skin_tones": "Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Cool,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 2299,
        "age_group": "Adults",
        "material": "Rayon",
        "season": "All Season",
        "available_sizes": "S,M,L,XL,XXL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A teal Anarkali-style kurti designed for festive and traditional occasions."
    },


    # ========================================================
    # CO-ORD SET
    # ========================================================

    {
        "outfit_id": "W024",
        "outfit_name": "Beige Casual Co-Ord Set",
        "category": "Women",
        "clothing_type": "Co-Ord Set",
        "colour": "Beige",
        "pattern": "Solid",
        "style": "Casual",
        "occasion": "Casual",
        "fit": "Relaxed",
        "suitable_body_shapes": "Rectangle,Hourglass,Apple,Pear",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep",
        "suitable_undertones": "Warm,Neutral",
        "suitable_proportion_types": "Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 180,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 2399,
        "age_group": "Adults",
        "material": "Cotton Blend",
        "season": "Spring,Summer,Autumn",
        "available_sizes": "XS,S,M,L,XL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A relaxed beige co-ord set designed for comfortable everyday casual wear."
    },


    # ========================================================
    # OFFICE OUTFIT
    # ========================================================

    {
        "outfit_id": "W025",
        "outfit_name": "Charcoal Professional Office Set",
        "category": "Women",
        "clothing_type": "Formal Set",
        "colour": "Charcoal Grey",
        "pattern": "Solid",
        "style": "Formal",
        "occasion": "Office",
        "fit": "Structured",
        "suitable_body_shapes": "Apple,Rectangle,Inverted Triangle,Hourglass",
        "suitable_skin_tones": "Very Fair,Fair,Light,Medium,Tan,Deep,Dark",
        "suitable_undertones": "Warm,Cool,Neutral",
        "suitable_proportion_types": "Wider Shoulders,Wider Hips,Balanced",
        "min_height_cm": 145,
        "max_height_cm": 185,
        "image_path": None,
        "tryon_image_path": None,
        "product_store": "AI Style Collection",
        "price": 3299,
        "age_group": "Adults",
        "material": "Polyester Viscose Blend",
        "season": "All Season",
        "available_sizes": "XS,S,M,L,XL,XXL",
        "brand": "AI Style Collection",
        "product_url": None,
        "description": "A structured charcoal formal set designed for professional office styling."
    }
]


# ============================================================
# INSERT / UPDATE FUNCTION
# ============================================================

def add_women_outfits():

    print("=" * 60)
    print("ADDING WOMEN OUTFITS")
    print("=" * 60)

    if not DB_PATH.exists():

        print(
            f"ERROR: Database not found:\n{DB_PATH}"
        )

        return

    connection = sqlite3.connect(
        DB_PATH
    )

    connection.row_factory = sqlite3.Row

    try:

        # ----------------------------------------------------
        # Make sure all required columns exist
        # ----------------------------------------------------

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(clothing)"
            ).fetchall()
        }

        required_columns = {
            "age_group",
            "material",
            "season",
            "available_sizes",
            "brand",
            "product_url",
            "description"
        }

        missing_columns = (
            required_columns -
            existing_columns
        )

        if missing_columns:

            print(
                "ERROR: Some new database columns are missing:"
            )

            for column in sorted(
                missing_columns
            ):
                print(
                    f"  - {column}"
                )

            print(
                "\nPlease run migrate_clothing_db.py first."
            )

            return

        # ----------------------------------------------------
        # Insert / update records
        # ----------------------------------------------------

        inserted = 0
        updated = 0

        for outfit in WOMEN_OUTFITS:

            existing = connection.execute(
                """
                SELECT id
                FROM clothing
                WHERE outfit_id = ?
                """,
                (
                    outfit["outfit_id"],
                )
            ).fetchone()

            values = (
                outfit["outfit_id"],
                outfit["outfit_name"],
                outfit["category"],
                outfit["clothing_type"],
                outfit["colour"],
                outfit["pattern"],
                outfit["style"],
                outfit["occasion"],
                outfit["fit"],
                outfit["suitable_body_shapes"],
                outfit["suitable_skin_tones"],
                outfit["suitable_undertones"],
                outfit["suitable_proportion_types"],
                outfit["min_height_cm"],
                outfit["max_height_cm"],
                outfit["image_path"],
                outfit["tryon_image_path"],
                outfit["product_store"],
                outfit["price"],
                outfit["age_group"],
                outfit["material"],
                outfit["season"],
                outfit["available_sizes"],
                outfit["brand"],
                outfit["product_url"],
                outfit["description"]
            )

            if existing:

                connection.execute(
                    """
                    UPDATE clothing
                    SET
                        outfit_name = ?,
                        category = ?,
                        clothing_type = ?,
                        colour = ?,
                        pattern = ?,
                        style = ?,
                        occasion = ?,
                        fit = ?,
                        suitable_body_shapes = ?,
                        suitable_skin_tones = ?,
                        suitable_undertones = ?,
                        suitable_proportion_types = ?,
                        min_height_cm = ?,
                        max_height_cm = ?,
                        image_path = ?,
                        tryon_image_path = ?,
                        product_store = ?,
                        price = ?,
                        age_group = ?,
                        material = ?,
                        season = ?,
                        available_sizes = ?,
                        brand = ?,
                        product_url = ?,
                        description = ?
                    WHERE outfit_id = ?
                    """,
                    (
                        outfit["outfit_name"],
                        outfit["category"],
                        outfit["clothing_type"],
                        outfit["colour"],
                        outfit["pattern"],
                        outfit["style"],
                        outfit["occasion"],
                        outfit["fit"],
                        outfit["suitable_body_shapes"],
                        outfit["suitable_skin_tones"],
                        outfit["suitable_undertones"],
                        outfit["suitable_proportion_types"],
                        outfit["min_height_cm"],
                        outfit["max_height_cm"],
                        outfit["image_path"],
                        outfit["tryon_image_path"],
                        outfit["product_store"],
                        outfit["price"],
                        outfit["age_group"],
                        outfit["material"],
                        outfit["season"],
                        outfit["available_sizes"],
                        outfit["brand"],
                        outfit["product_url"],
                        outfit["description"],
                        outfit["outfit_id"]
                    )
                )

                updated += 1

            else:

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
                        price,
                        age_group,
                        material,
                        season,
                        available_sizes,
                        brand,
                        product_url,
                        description
                    )
                    VALUES
                    (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    """,
                    values
                )

                inserted += 1

        connection.commit()

        # ----------------------------------------------------
        # Final counts
        # ----------------------------------------------------

        women_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM clothing
            WHERE category = 'Women'
            """
        ).fetchone()[0]

        total_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM clothing
            """
        ).fetchone()[0]

        print("\n" + "=" * 60)
        print("WOMEN CATALOGUE UPDATE COMPLETED")
        print("=" * 60)

        print(
            f"New records inserted: {inserted}"
        )

        print(
            f"Existing records updated: {updated}"
        )

        print(
            f"Total Women outfits: {women_count}"
        )

        print(
            f"Total outfits in database: {total_count}"
        )

        print("=" * 60)

    except Exception as error:

        connection.rollback()

        print("\nERROR while adding Women outfits:")
        print(error)

    finally:

        connection.close()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    add_women_outfits()