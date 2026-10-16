import pytest
from fastapi.testclient import TestClient

from app.main import app

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    body = client.get("/health").json()
    assert body["postgres"] is True
    assert body["redis"] is True


def test_recipes_loaded_from_migrations(client):
    r = client.get("/recipes")
    assert r.status_code == 200
    assert len(r.json()["recipes"]) > 0


def test_pantry_roundtrip(client):
    put = client.put("/pantry/ci_user", json={"items": [{"name": "flour", "grams": 500}]})
    assert put.status_code == 200
    got = client.get("/pantry/ci_user")
    assert got.status_code == 200
    assert got.json()["items"]["flour"] == 500.0


def test_pantry_converts_units(client):
    client.put("/pantry/unit_user", json={"items": [{"name": "flour", "qty": 2, "unit": "cup"}]})
    assert client.get("/pantry/unit_user").json()["items"]["flour"] == 240.0


def test_pantry_rejects_unknown_unit(client):
    r = client.put("/pantry/bad_user", json={"items": [{"name": "flour", "qty": 1, "unit": "stone"}]})
    assert r.status_code == 400


def test_cookable_has_three_buckets(client):
    client.put("/pantry/ci_user", json={"items": [{"name": "flour", "grams": 500}]})
    body = client.get("/pantry/ci_user/cookable").json()
    assert {"can_cook_now", "need_one_more", "need_more"} <= body.keys()


def test_shopping_list(client):
    recipe_id = client.get("/recipes").json()["recipes"][0]["id"]
    r = client.get(f"/recipes/{recipe_id}/shopping/ci_user")
    assert r.status_code == 200
    assert "shopping_list" in r.json()


def test_shopping_unknown_recipe_404(client):
    assert client.get("/recipes/999999/shopping/ci_user").status_code == 404


def test_delete_pantry_item(client):
    client.put(
        "/pantry/del_user",
        json={"items": [{"name": "flour", "grams": 500}, {"name": "sugar", "grams": 200}]},
    )
    r = client.delete("/pantry/del_user/flour")
    assert r.status_code == 200
    items = client.get("/pantry/del_user").json()["items"]
    assert "flour" not in items
    assert "sugar" in items


def test_delete_missing_item_404(client):
    assert client.delete("/pantry/del_user/nothing").status_code == 404
