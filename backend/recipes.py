import json
import os

RECIPES_PATH = os.path.join(os.path.dirname(__file__), "recipes.json")

with open(RECIPES_PATH, encoding="utf-8") as f:
    _RECIPES = json.load(f)


def all_recipes() -> list[dict]:
    return _RECIPES


def search(query: str) -> list[dict]:
    """Match a query against drink names and ingredient names (case-insensitive)."""
    q = query.strip().lower()
    if not q:
        return _RECIPES
    results = []
    for recipe in _RECIPES:
        if q in recipe["name"].lower():
            results.append(recipe)
            continue
        if any(q in ing["name"].lower() for ing in recipe["ingredients"]):
            results.append(recipe)
    return results


# Everything in the recipe book that carries alcohol, and roughly how much.
# Two things read this: the "Light" pour, which cuts these back and leaves the
# mixers alone (same size glass, weaker drink), and the potency meter, which
# needs the actual strengths rather than a plain yes/no.
ABV = {
    "vodka": 0.40,
    "gin": 0.40,
    "white rum": 0.40,
    "dark rum": 0.40,
    "tequila": 0.40,
    "whiskey": 0.40,
    "triple sec": 0.30,
    "blue curacao": 0.25,
    "midori": 0.20,
}

# Derived rather than written out twice — a bottle with an ABV is a spirit.
SPIRITS = {name for name, abv in ABV.items() if abv > 0}

# How much liquor the UI's "Light" button pours. Served to the frontend so the
# button and the potency meter can't drift apart.
LIGHT_STRENGTH = 0.6

# One US standard drink is 14 g of ethanol ≈ 17.7 ml.
STANDARD_DRINK_ML = 17.7

# Bands for the 5-bar meter, in score (see `potency`). Tuned against this
# recipe book rather than to round numbers: a one-shot highball — which is
# most of the menu — should land in the middle, and a straight shot at the top.
POTENCY_BANDS = (0.38, 0.46, 0.56, 0.70)
POTENCY_LABELS = ("ZERO PROOF", "EASY", "MEDIUM", "STIFF", "STRONG", "ROCKET FUEL")


def is_spirit(name: str) -> bool:
    return name.strip().lower() in SPIRITS


def potency(recipe: dict, strength: float = 1.0) -> dict:
    """How hard a drink hits, as a 0–5 level plus the numbers behind it.

    Two things matter to whoever is holding the glass and neither one alone is
    enough: how much alcohol is in it (standard drinks) and how concentrated
    that alcohol is (ABV). A straight shot and a vodka cranberry carry the same
    ounce of vodka, but nobody sips the shot. So the level is a blend, weighted
    toward the total and nudged by the concentration.

    Manual ingredients count here even though no pump touches them — the splash
    of Sprite is still in the glass, still diluting the drink.
    """
    alcohol_ml = 0.0
    total_ml = 0.0
    for ing in recipe["ingredients"]:
        abv = ABV.get(ing["name"].strip().lower(), 0.0)
        ml = ing["ml"] * strength if abv else ing["ml"]
        alcohol_ml += ml * abv
        total_ml += ml

    abv = alcohol_ml / total_ml if total_ml else 0.0
    standard_drinks = alcohol_ml / STANDARD_DRINK_ML
    score = 0.6 * min(1.0, standard_drinks / 2.0) + 0.4 * min(1.0, abv / 0.40)
    level = 0 if alcohol_ml <= 0 else sum(score >= b for b in POTENCY_BANDS) + 1

    return {
        "level": level,
        "label": POTENCY_LABELS[level],
        "abv": round(abv * 100, 1),
        "standard_drinks": round(standard_drinks, 2),
        "alcohol_ml": round(alcohol_ml, 1),
        "volume_ml": round(total_ml, 1),
    }


# Potency is a pure function of a static recipe book, so it is worked out once
# at import and rides along on every recipe the API hands out. Both strengths
# are shipped because the modal's Light button has to redraw the meter with no
# round trip.
for _recipe in _RECIPES:
    _recipe["potency"] = potency(_recipe)
    _recipe["potency_light"] = potency(_recipe, LIGHT_STRENGTH)


def pumped_ingredients(recipe: dict) -> list[dict]:
    """The ingredients a pump actually dispenses.

    Anything flagged `"manual": true` — the splash of Sprite, the float of
    cola — is topped up by hand at the glass, so it never reaches a pump and
    must not count against whether a drink can be made.
    """
    return [ing for ing in recipe["ingredients"] if not ing.get("manual")]


def ingredient_vocabulary() -> list[str]:
    """Every distinct ingredient used across all recipes, sorted."""
    names = {ing["name"] for recipe in _RECIPES for ing in recipe["ingredients"]}
    return sorted(names)


def annotate_availability(available_names: list[str]) -> list[dict]:
    """Tag each recipe with whether it can be made from the available ingredients.

    Matching is case-insensitive and ignores surrounding whitespace.
    """
    available = {name.strip().lower() for name in available_names if name.strip()}
    annotated = []
    for recipe in _RECIPES:
        missing = [
            ing["name"]
            for ing in pumped_ingredients(recipe)
            if ing["name"].strip().lower() not in available
        ]
        annotated.append({**recipe, "available": not missing, "missing": missing})
    return annotated
