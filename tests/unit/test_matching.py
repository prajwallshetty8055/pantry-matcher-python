import pytest

from app.matching import (
    UnitError,
    classify_recipes,
    have_enough,
    normalise,
    to_base,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("flour", "flour"),
        ("  Flour ", "flour"),
        ("Oats", "oat"),
        ("", ""),
        (None, ""),
    ],
)
def test_normalise(raw, expected):
    assert normalise(raw) == expected


@pytest.mark.parametrize(
    "qty, unit, liquid, expected",
    [
        (250, "g", False, 250.0),
        (1, "kg", False, 1000.0),
        (2, "cup", False, 240.0),
        (2, "tbsp", False, 30.0),
        (3, "tsp", False, 15.0),
        (2, "piece", False, 100.0),
        (500, "ml", True, 500.0),
        (1, "l", True, 1000.0),
        (1, "cup", True, 240.0),
        (2, "tbsp", True, 30.0),
        ("2", "cup", False, 240.0),
        (1, "  CUP ", False, 120.0),
        (0, "g", False, 0.0),
    ],
)
def test_to_base_conversions(qty, unit, liquid, expected):
    assert to_base(qty, unit, liquid=liquid) == expected


def test_cup_differs_for_solids_and_liquids():
    assert to_base(1, "cup") == 120.0
    assert to_base(1, "cup", liquid=True) == 240.0


def test_different_units_of_same_amount_are_equal():
    assert to_base(0.5, "kg") == to_base(500, "g")
    assert to_base(1, "cup") == to_base(8, "tbsp")


@pytest.mark.parametrize(
    "qty, unit, liquid",
    [
        (-1, "g", False),
        ("abc", "g", False),
        (None, "g", False),
        (1, "stone", False),
        (1, "l", False),
        (1, "piece", True),
        (1, None, False),
    ],
)
def test_to_base_rejects_bad_input(qty, unit, liquid):
    with pytest.raises(UnitError):
        to_base(qty, unit, liquid=liquid)


def test_unit_error_is_a_value_error():
    assert issubclass(UnitError, ValueError)


def test_have_enough_exact_match():
    ok, missing = have_enough({"flour": 500.0}, {"flour": 500.0})
    assert ok is True
    assert missing == {}


def test_have_enough_reports_shortfall():
    ok, missing = have_enough({"flour": 200.0}, {"flour": 500.0})
    assert ok is False
    assert missing == {"flour": 300.0}


def test_have_enough_missing_ingredient_entirely():
    ok, missing = have_enough({}, {"egg": 100.0})
    assert not ok
    assert missing == {"egg": 100.0}


def test_have_enough_normalises_needed_names():
    ok, missing = have_enough({"oat": 10.0}, {"Oats": 50.0})
    assert not ok
    assert missing == {"oat": 40.0}


def test_have_enough_rounds_shortfall():
    _, missing = have_enough({"flour": 0.0}, {"flour": 10.126})
    assert missing == {"flour": 10.13}


def test_have_enough_uses_substitute():
    ok, missing = have_enough({"oil": 100.0}, {"butter": 100.0})
    assert ok
    assert missing == {}


def test_have_enough_combines_ingredient_and_substitute():
    ok, _ = have_enough({"butter": 50.0, "oil": 60.0}, {"butter": 100.0})
    assert ok


def test_have_enough_substitute_still_short():
    ok, missing = have_enough({"butter": 20.0, "oil": 30.0}, {"butter": 100.0})
    assert not ok
    assert missing == {"butter": 50.0}


def test_have_enough_substitutes_can_be_disabled():
    ok, missing = have_enough({"oil": 100.0}, {"butter": 100.0}, allow_substitutes=False)
    assert not ok
    assert missing == {"butter": 100.0}


def _recipe(rid, name, needs):
    return {"id": rid, "name": name, "needs": needs}


def test_classify_empty_recipe_list():
    assert classify_recipes({"flour": 1.0}, []) == {
        "can_cook_now": [],
        "need_one_more": [],
        "need_more": [],
    }


def test_classify_splits_into_three_buckets():
    pantry = {"flour": 500.0, "egg": 100.0}
    recipes = [
        _recipe(1, "Pancakes", {"flour": 200.0, "egg": 50.0}),
        _recipe(2, "Cake", {"flour": 200.0, "sugar": 100.0}),
        _recipe(3, "Feast", {"rice": 100.0, "dal": 100.0}),
    ]
    result = classify_recipes(pantry, recipes)
    assert [r["id"] for r in result["can_cook_now"]] == [1]
    assert [r["id"] for r in result["need_one_more"]] == [2]
    assert result["need_one_more"][0]["missing"] == {"sugar": 100.0}
    assert [r["id"] for r in result["need_more"]] == [3]


def test_classify_recipe_with_no_needs_is_cookable():
    result = classify_recipes({}, [_recipe(1, "Water", {})])
    assert [r["id"] for r in result["can_cook_now"]] == [1]


def test_classify_counts_substitutes():
    result = classify_recipes({"ghee": 100.0}, [_recipe(1, "Toast", {"butter": 50.0})])
    assert [r["id"] for r in result["can_cook_now"]] == [1]


def test_classify_sorts_by_missing_count_then_name():
    recipes = [
        _recipe(1, "Zeta", {"a": 1.0}),
        _recipe(2, "Alpha", {"a": 1.0}),
        _recipe(3, "Three", {"a": 1.0, "b": 1.0, "c": 1.0}),
        _recipe(4, "Two", {"a": 1.0, "b": 1.0}),
    ]
    result = classify_recipes({}, recipes)
    assert [r["name"] for r in result["need_one_more"]] == ["Alpha", "Zeta"]
    assert [r["name"] for r in result["need_more"]] == ["Two", "Three"]
