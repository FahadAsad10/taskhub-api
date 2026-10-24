from datetime import date, timedelta

from tests.conftest import register_and_login


def make_project(client, auth, name="Launch"):
    res = client.post("/projects", json={"name": name, "description": "Ship v1"}, headers=auth)
    assert res.status_code == 201
    return res.json()["id"]


def test_project_crud(client, auth):
    pid = make_project(client, auth)
    assert client.get(f"/projects/{pid}", headers=auth).json()["name"] == "Launch"

    res = client.patch(f"/projects/{pid}", json={"name": "Launch v2"}, headers=auth)
    assert res.json()["name"] == "Launch v2"
    assert res.json()["description"] == "Ship v1"

    page = client.get("/projects", headers=auth).json()
    assert page["total"] == 1

    assert client.delete(f"/projects/{pid}", headers=auth).status_code == 204
    assert client.get(f"/projects/{pid}", headers=auth).status_code == 404


def test_users_cannot_see_each_others_projects(client, auth):
    pid = make_project(client, auth)
    other = register_and_login(client, "eve@example.com")
    assert client.get(f"/projects/{pid}", headers=other).status_code == 404
    assert client.get(f"/projects/{pid}/tasks", headers=other).status_code == 404
    assert client.get("/projects", headers=other).json()["total"] == 0


def test_task_filters_search_and_pagination(client, auth):
    pid = make_project(client, auth)
    url = f"/projects/{pid}/tasks"
    for i in range(5):
        client.post(url, json={"title": f"Write docs part {i}", "priority": "low"}, headers=auth)
    client.post(url, json={"title": "Fix login bug", "priority": "high", "status": "in_progress"}, headers=auth)

    assert client.get(url, headers=auth).json()["total"] == 6
    assert client.get(url, params={"status": "in_progress"}, headers=auth).json()["total"] == 1
    assert client.get(url, params={"priority": "low"}, headers=auth).json()["total"] == 5
    assert client.get(url, params={"q": "login"}, headers=auth).json()["items"][0]["title"] == "Fix login bug"

    page = client.get(url, params={"limit": 2, "offset": 4, "sort": "title", "order": "asc"}, headers=auth).json()
    assert [t["title"] for t in page["items"]] == ["Write docs part 3", "Write docs part 4"]


def test_task_update_and_delete(client, auth):
    pid = make_project(client, auth)
    tid = client.post(f"/projects/{pid}/tasks", json={"title": "Draft"}, headers=auth).json()["id"]

    res = client.patch(f"/projects/{pid}/tasks/{tid}", json={"status": "done"}, headers=auth)
    assert res.status_code == 200
    assert res.json()["status"] == "done"

    assert client.delete(f"/projects/{pid}/tasks/{tid}", headers=auth).status_code == 204
    assert client.get(f"/projects/{pid}/tasks/{tid}", headers=auth).status_code == 404


def test_task_from_another_project_is_not_found(client, auth):
    a = make_project(client, auth, "A")
    b = make_project(client, auth, "B")
    tid = client.post(f"/projects/{a}/tasks", json={"title": "Only in A"}, headers=auth).json()["id"]
    assert client.get(f"/projects/{b}/tasks/{tid}", headers=auth).status_code == 404


def test_stats(client, auth):
    pid = make_project(client, auth)
    url = f"/projects/{pid}/tasks"
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client.post(url, json={"title": "Done one", "status": "done"}, headers=auth)
    client.post(url, json={"title": "Late one", "due_date": yesterday}, headers=auth)
    client.post(url, json={"title": "Working", "status": "in_progress"}, headers=auth)
    client.post(url, json={"title": "Late but done", "status": "done", "due_date": yesterday}, headers=auth)

    stats = client.get(f"/projects/{pid}/stats", headers=auth).json()
    assert stats == {"total": 4, "todo": 1, "in_progress": 1, "done": 2, "overdue": 1, "completion_rate": 0.5}


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"
