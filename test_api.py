import os, tempfile
os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mkdtemp()}/t.db"
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)

def test_flow():
    py = c.post("/skills", json={"name": "Python"}).json()["id"]
    ml = c.post("/skills", json={"name": "ML"}).json()["id"]
    role = c.post("/roles", json={"name": "Data Scientist", "requirements": [
        {"skill_id": py, "level": 4}, {"skill_id": ml, "level": 4}]}).json()["id"]
    c.post("/employees/bulk", json=[{"external_id": "a", "name": "Ann"}, {"external_id": "b", "name": "Bob"}])
    ids = [e["id"] for e in c.get("/employees").json()["items"]]
    c.put(f"/employees/{ids[0]}/ratings", json=[{"skill_id": py, "level": 4}, {"skill_id": ml, "level": 2}])
    c.put(f"/employees/{ids[1]}/ratings", json=[{"skill_id": py, "level": 5}, {"skill_id": ml, "level": 5}])
    d = c.get(f"/employees/{ids[0]}/readiness/{role}").json()
    assert d["score"] == 75.0 and d["gaps"][0]["skill"] == "ML" and d["total_est_hours"] == 50   # (4+2)/(4+4)
    top = c.get(f"/roles/{role}/candidates").json()["items"]
    assert [x["name"] for x in top] == ["Bob", "Ann"] and top[0]["score"] == 100.0
    # NEW role at runtime + changing requirements recomputes (background task runs in TestClient)
    r2 = c.post("/roles", json={"name": "ML Lead", "requirements": [{"skill_id": ml, "level": 5}]}).json()["id"]
    assert c.get(f"/roles/{r2}/candidates").json()["items"][0]["name"] == "Bob"
    c.put(f"/roles/{role}/requirements", json=[{"skill_id": py, "level": 2}])
    assert c.get(f"/employees/{ids[0]}/readiness/{role}").json()["score"] == 100.0
    c.put(f"/demand/{ml}", params={"target_headcount": 3})
    plan = {p["skill"]: p for p in c.get("/analytics/workforce-plan").json()}
    assert plan["ML"]["supply"] == 1 and plan["ML"]["shortfall"] == 2 and plan["ML"]["upskill_pool"] == 1

def test_pagination():
    c.post("/employees/bulk", json=[{"external_id": f"p{i}", "name": f"P{i}"} for i in range(30)])
    p1 = c.get("/employees", params={"limit": 10}).json(); p2 = c.get("/employees", params={"limit": 10, "after": p1["next_after"]}).json()
    assert not {e["id"] for e in p1["items"]} & {e["id"] for e in p2["items"]}

def test_ui_and_detail_endpoints():
    r = c.get("/"); assert r.status_code == 200 and "SkillGraph" in r.text
    sk = c.post("/skills", json={"name": "Go"}).json()["id"]
    role = c.post("/roles", json={"name": "Backend", "requirements": [{"skill_id": sk, "level": 3}]}).json()["id"]
    c.post("/employees/bulk", json=[{"external_id": "u1", "name": "Uma"}])
    eid = [e for e in c.get("/employees", params={"limit": 200}).json()["items"] if e["external_id"] == "u1"][0]["id"]
    c.put(f"/employees/{eid}/ratings", json=[{"skill_id": sk, "level": 3}])
    assert c.get(f"/employees/{eid}").json()["ratings"][0]["level"] == 3
    assert c.get(f"/employees/{eid}/top-roles").json()[0]["score"] == 100.0
    assert c.get("/analytics/summary").json()["roles"] >= 1

def test_solution_features():
    s = [c.post("/skills", json={"name": n}).json()["id"] for n in ("Sk1", "Sk2")]
    role = c.post("/roles", json={"name": "Crit", "is_critical": True, "requirements": [
        {"skill_id": s[0], "level": 4}, {"skill_id": s[1], "level": 3}]}).json()["id"]
    c.post("/employees/bulk", json=[{"external_id": "i1", "name": "Inc", "current_role_id": role},
        {"external_id": "s1", "name": "Succ"}, {"external_id": "s2", "name": "=Succ2", "availability": 50}])
    ids = {e["external_id"]: e["id"] for e in c.get("/employees", params={"limit": 200}).json()["items"]}
    c.put(f"/employees/{ids['s1']}/ratings", json=[{"skill_id": s[0], "level": 5}, {"skill_id": s[1], "level": 4}])
    c.put(f"/employees/{ids['s2']}/ratings", json=[{"skill_id": s[0], "level": 3}, {"skill_id": s[1], "level": 2}])
    sx = c.get(f"/succession/{role}").json()   # s1 = 100% (ready now), s2 = 5/7 = 71% (ready soon), Inc is excluded as incumbent
    assert sx["bands"]["ready_now"]["top"][0]["name"] == "Succ" and sx["bands"]["ready_soon"]["count"] == 1 and sx["risk"] in ("low", "medium")
    ov = [x for x in c.get("/succession").json() if x["role_id"] == role][0]
    assert ov["incumbents"] == 1 and ov["ready_now"] == 1
    pid = c.post("/projects", json={"name": "Proj", "skills": [{"skill_id": s[0], "level": 4}]}).json()["id"]
    assert [x["name"] for x in c.get(f"/projects/{pid}/staffing", params={"min_available": 80}).json()["items"]] == ["Succ"]
    c.post("/learning", json={"skill_id": s[1], "title": "Sk2 advanced", "level": 3, "hours": 20, "url": "https://x.io"})
    assert c.post("/learning", json={"skill_id": s[1], "title": "bad", "level": 3, "hours": 1, "url": "javascript:alert(1)"}).status_code == 422
    plan = c.get(f"/employees/{ids['s2']}/development-plan/{role}").json()
    assert plan["steps"][0]["skill"] in ("Sk1", "Sk2") and any(st["resources"] for st in plan["steps"]) and plan["total_hours"] >= 20
    rep = c.get("/reports/role-readiness.csv", params={"role_id": role}).text
    assert "Succ" in rep and "'=Succ2" in rep   # formula injection neutralised
    assert c.get("/reports/succession.csv").status_code == 200 and c.get("/reports/skill-matrix.csv").status_code == 200
    risks = c.get("/analytics/continuity-risks").json()
    assert any(x["skill"] == "Sk1" for x in risks["skills_at_risk"])
    assert c.post(f"/employees/{ids['s1']}/extract-skills", json={"text": "x"}).status_code == 503  # needs ANTHROPIC_API_KEY
