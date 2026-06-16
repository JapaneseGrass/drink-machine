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
            for ing in recipe["ingredients"]
            if ing["name"].strip().lower() not in available
        ]
        annotated.append({**recipe, "available": not missing, "missing": missing})
    return annotated
