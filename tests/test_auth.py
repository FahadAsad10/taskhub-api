def test_register_and_me(client):
    res = client.post(
        "/auth/register", json={"email": "Grace@Example.com", "full_name": "Grace Hopper", "password": "compilers!"}
    )
    assert res.status_code == 201
    assert res.json()["email"] == "grace@example.com"
    assert "hashed_password" not in res.json()

    token = client.post("/auth/token", data={"username": "grace@example.com", "password": "compilers!"}).json()
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token['access_token']}"})
    assert me.status_code == 200
    assert me.json()["full_name"] == "Grace Hopper"


def test_duplicate_email_rejected(client):
    body = {"email": "dup@example.com", "full_name": "Dup", "password": "password1"}
    assert client.post("/auth/register", json=body).status_code == 201
    assert client.post("/auth/register", json=body).status_code == 409


def test_wrong_password(client):
    client.post("/auth/register", json={"email": "x@example.com", "full_name": "X", "password": "password1"})
    res = client.post("/auth/token", data={"username": "x@example.com", "password": "nope-nope"})
    assert res.status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/projects").status_code == 401
    assert client.get("/projects", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_short_password_rejected(client):
    res = client.post("/auth/register", json={"email": "s@example.com", "full_name": "S", "password": "short"})
    assert res.status_code == 422
