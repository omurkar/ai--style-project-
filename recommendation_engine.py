from typing import Dict, List, Optional, Tuple


# =========================================================
# RECOMMENDATION SCORING ENGINE
# =========================================================

def _split_values(value: Optional[str]) -> List[str]:

    if not value:
        return []

    return [
        item.strip().lower()
        for item in value.split(",")
        if item.strip()
    ]


def _matches(
    value: Optional[str],
    target: Optional[str]
) -> bool:

    if not value or not target:
        return False

    return target.strip().lower() in _split_values(value)


def _height_score(
    height_cm: Optional[float],
    min_height: Optional[float],
    max_height: Optional[float]
) -> Tuple[int, str]:

    if height_cm is None:
        return 0, "Height was not provided."

    if min_height is None or max_height is None:
        return 5, "Height range is not specified."

    if min_height <= height_cm <= max_height:

        return (
            10,
            "Your height is within the suitable range."
        )

    distance = min(
        abs(height_cm - min_height),
        abs(height_cm - max_height)
    )

    if distance <= 5:

        return (
            5,
            "Your height is close to the suitable range."
        )

    return (
        0,
        "Your height is outside the preferred range."
    )


# =========================================================
# SCORE ONE OUTFIT
# =========================================================

def score_outfit(
    profile: Dict,
    outfit: Dict
) -> Dict:

    score = 0

    reasons = []

    matched_dimensions = []

    maximum_score = 90


    # -----------------------------------------------------
    # CATEGORY - 20 POINTS
    # -----------------------------------------------------

    if (
        profile.get("category")
        and outfit.get("category", "").lower()
        == profile["category"].lower()
    ):

        score += 20

        matched_dimensions.append(
            "category"
        )

        reasons.append(
            "made for your category"
        )


    # -----------------------------------------------------
    # BODY SHAPE - 20 POINTS
    # -----------------------------------------------------

    body_shape = profile.get(
        "body_shape"
    )


    if body_shape:

        if _matches(
            outfit.get("suitable_body_shapes"),
            body_shape
        ):

            score += 20

            matched_dimensions.append(
                "body shape"
            )

            reasons.append(
                f"works with your "
                f"{body_shape.lower()} body shape"
            )


    # -----------------------------------------------------
    # SKIN TONE - 15 POINTS
    # -----------------------------------------------------

    skin_tone = profile.get(
        "skin_tone"
    )


    if skin_tone:

        if _matches(
            outfit.get("suitable_skin_tones"),
            skin_tone
        ):

            score += 15

            matched_dimensions.append(
                "skin tone"
            )

            reasons.append(
                f"suits your "
                f"{skin_tone.lower()} skin tone"
            )


    # -----------------------------------------------------
    # UNDERTONE - 15 POINTS
    # -----------------------------------------------------

    undertone = profile.get(
        "undertone"
    )


    if (
        undertone
        and undertone.lower()
        != "not determined"
    ):

        if _matches(
            outfit.get("suitable_undertones"),
            undertone
        ):

            score += 15

            matched_dimensions.append(
                "undertone"
            )

            reasons.append(
                f"complements your "
                f"{undertone.lower()} undertone"
            )


    # -----------------------------------------------------
    # BODY PROPORTIONS - 10 POINTS
    # -----------------------------------------------------

    proportions = profile.get(
        "body_proportions"
    )


    if proportions:

        if _matches(
            outfit.get("suitable_proportion_types"),
            proportions
        ):

            score += 10

            matched_dimensions.append(
                "proportions"
            )

            reasons.append(
                f"works with your "
                f"{proportions.lower()} proportions"
            )


    # -----------------------------------------------------
    # HEIGHT - 10 POINTS
    # -----------------------------------------------------

    height_points, height_reason = _height_score(
        profile.get("height_cm"),
        outfit.get("min_height_cm"),
        outfit.get("max_height_cm")
    )

    score += height_points


    if height_points == 10:

        matched_dimensions.append(
            "height"
        )

        reasons.append(
            "falls within your suitable height range"
        )

    elif height_points == 5:

        reasons.append(
            "is close to your suitable height range"
        )


    # -----------------------------------------------------
    # NORMALIZE SCORE
    # -----------------------------------------------------

    score = round(
        (score / maximum_score) * 100
    )

    score = max(
        0,
        min(100, score)
    )


    # -----------------------------------------------------
    # WHY WE RECOMMEND IT
    # -----------------------------------------------------

    if reasons:

        if len(reasons) == 1:

            explanation = (
                reasons[0].capitalize()
                + "."
            )

        elif len(reasons) == 2:

            explanation = (
                reasons[0].capitalize()
                + " and "
                + reasons[1]
                + "."
            )

        else:

            explanation = (
                ", ".join(
                    reasons[:3]
                ).capitalize()
                + "."
            )

    else:

        explanation = (
            "This outfit is available for your "
            "selected category and can be considered "
            "as an alternative style."
        )


    result = dict(
        outfit
    )

    result["match_score"] = score

    result["why_recommended"] = explanation

    result["matched_dimensions"] = (
        matched_dimensions
    )


    return result


# =========================================================
# GET PERSONALIZED RECOMMENDATIONS
# =========================================================

def get_recommendations(
    profile: Dict,
    clothing_rows: List[Dict],
    occasion: str = "All Occasions",
    style: str = "All Styles",
    budget: str = "Any Budget",
    limit: int = 12
) -> List[Dict]:

    filtered = []

    # Dynamic session profile preferences
    user_pref_occasion = (profile.get("preferred_occasion") or "").strip().lower()
    user_pref_style = (profile.get("preferred_style") or "").strip().lower()
    user_budget = profile.get("budget")

    # Target occasion: dropdown filter takes precedence, fallback to saved profile preference
    target_occasion = occasion.lower() if occasion and occasion != "All Occasions" else user_pref_occasion
    target_style = style.lower() if style and style != "All Styles" else user_pref_style

    # =====================================================
    # FILTER CLOTHING STRICTLY AGAINST PROFILE PREFERENCES
    # =====================================================

    for outfit in clothing_rows:

        # -------------------------------------------------
        # CATEGORY
        # -------------------------------------------------

        if (
            profile.get("category")
            and outfit.get("category", "").lower()
            != profile["category"].lower()
        ):
            continue

        # -------------------------------------------------
        # STRICT BUDGET LIMIT FILTERING
        # -------------------------------------------------

        price = float(outfit.get("price") or 0)

        # Dropdown budget filter
        if budget == "Under ₹1000" and price >= 1000:
            continue
        if budget == "Under ₹1500" and price >= 1500:
            continue
        if budget == "Under ₹2000" and price >= 2000:
            continue
        if budget == "Under ₹2500" and price >= 2500:
            continue
        if budget == "Under ₹3000" and price >= 3000:
            continue

        # Saved user profile budget limit (e.g. < 1000)
        if user_budget is not None and user_budget != "":
            try:
                max_allowed = float(user_budget)
                if max_allowed > 0 and price > max_allowed:
                    continue
            except (ValueError, TypeError):
                pass

        # -------------------------------------------------
        # OCCASION MATCHING (Formals, Parties, Casual, etc.)
        # -------------------------------------------------

        if target_occasion and target_occasion not in ["all occasions", "all"]:
            outfit_occ = (outfit.get("occasion") or "").lower()
            outfit_sty = (outfit.get("style") or "").lower()
            combined_occ_sty = f"{outfit_occ} {outfit_sty}"
            # Match singular/plural e.g. "formals" vs "formal", "parties" vs "party"
            occ_tokens = [
                target_occasion,
                target_occasion.rstrip("s"),
                target_occasion.replace("parties", "party"),
                target_occasion.replace("formals", "formal")
            ]
            matched_occ = any(t in combined_occ_sty or combined_occ_sty in t for t in occ_tokens if t)
            if not matched_occ:
                continue

        # -------------------------------------------------
        # STYLE MATCHING
        # -------------------------------------------------

        if target_style and target_style not in ["all styles", "all"]:
            outfit_sty = (outfit.get("style") or "").lower()
            if target_style not in outfit_sty and outfit_sty not in target_style:
                continue

        filtered.append(outfit)


    # =====================================================
    # SCORE ALL FILTERED OUTFITS
    # =====================================================

    scored = [

        score_outfit(
            profile,
            outfit
        )

        for outfit in filtered

    ]


    # Highest score first
    # Lower price first if scores are equal.

    scored.sort(
        key=lambda item: (
            -item["match_score"],
            float(
                item.get("price") or 0
            )
        )
    )


    return scored[:limit]