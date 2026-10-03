import os
import tempfile

import backend.app as app_module


def test_families_are_isolated():
    with tempfile.TemporaryDirectory() as temp:
        app_module.MASTER_DB = os.path.join(temp, "master.db")
        app_module.FAMILY_DB_DIR = os.path.join(temp, "databases")
        app_module.UPLOAD_DIR = os.path.join(temp, "uploads")
        os.makedirs(app_module.FAMILY_DB_DIR, exist_ok=True)
        os.makedirs(app_module.UPLOAD_DIR, exist_ok=True)
        app_module.init_master_database()

        client = app_module.app.test_client()

        family_a = client.post(
            "/api/families/create",
            json={
                "family_name": "Family A",
                "name": "Alice",
                "email": "alice@example.com",
                "password": "secret123",
                "relationship": "Daughter",
            },
        )
        assert family_a.status_code == 201
        a_data = family_a.get_json()
        a_token = a_data["token"]
        a_family = a_data["user"]["family"]

        family_b = client.post(
            "/api/families/create",
            json={
                "family_name": "Family B",
                "name": "Bob",
                "email": "bob@example.com",
                "password": "secret123",
                "relationship": "Son",
            },
        )
        assert family_b.status_code == 201
        b_data = family_b.get_json()
        b_token = b_data["token"]

        joined = client.post(
            "/api/families/join",
            json={
                "join_code": a_family["join_code"],
                "name": "Anita",
                "email": "anita@example.com",
                "password": "secret123",
                "relationship": "Granddaughter",
            },
        )
        assert joined.status_code == 201

        a_family_response = client.get(
            "/api/family", headers={"Authorization": f"Bearer {a_token}"}
        )
        assert a_family_response.status_code == 200
        assert len(a_family_response.get_json()["members"]) == 2

        members = a_family_response.get_json()["members"]
        anita = next(member for member in members if member["name"] == "Anita")

        created = client.post(
            "/api/memories",
            headers={"Authorization": f"Bearer {a_token}"},
            data={
                "member_id": str(anita["id"]),
                "title": "A family story",
                "memory_text": "Our family remembers the old village school.",
            },
        )
        assert created.status_code == 201
        memory_id = created.get_json()["id"]

        a_memories = client.get(
            "/api/memories", headers={"Authorization": f"Bearer {a_token}"}
        )
        assert a_memories.status_code == 200
        assert len(a_memories.get_json()) == 1

        b_memories = client.get(
            "/api/memories", headers={"Authorization": f"Bearer {b_token}"}
        )
        assert b_memories.status_code == 200
        assert b_memories.get_json() == []

        cross_family = client.get(
            f"/api/memories/{memory_id}",
            headers={"Authorization": f"Bearer {b_token}"},
        )
        assert cross_family.status_code == 404

        a_db = os.path.join(
            app_module.FAMILY_DB_DIR, f"family_{a_family['id']}.db"
        )
        b_family = b_data["user"]["family"]
        b_db = os.path.join(
            app_module.FAMILY_DB_DIR, f"family_{b_family['id']}.db"
        )
        assert os.path.exists(a_db)
        assert os.path.exists(b_db)
        assert a_db != b_db
