"""Load synthetic data and time the readiness engine:  python -m scripts.seed --employees 1000000 --roles 50"""
import argparse, random, time
from sqlalchemy import func, insert, select
from app.db import Base, SessionLocal, engine
from app.models import Employee, Rating, Readiness, Role, RoleSkillReq, Skill
from app.readiness import recompute_role

ap = argparse.ArgumentParser()
ap.add_argument("--employees", type=int, default=20000); ap.add_argument("--skills", type=int, default=40)
ap.add_argument("--roles", type=int, default=10); ap.add_argument("--ratings", type=int, default=12)
a = ap.parse_args(); random.seed(1)
Base.metadata.create_all(engine)
t = time.time()
with SessionLocal() as s:
    s.execute(insert(Skill), [{"id": i, "name": f"Skill {i}", "category": f"Cat {i % 6}"} for i in range(1, a.skills + 1)])
    s.execute(insert(Role), [{"id": i, "name": f"Role {i}", "version": 1} for i in range(1, a.roles + 1)])
    s.execute(insert(RoleSkillReq), [{"role_id": r, "skill_id": k, "level": random.randint(1, 5), "weight": 1.0}
              for r in range(1, a.roles + 1) for k in random.sample(range(1, a.skills + 1), random.randint(8, 15))])
    s.commit()
    CH = 20_000
    for lo in range(0, a.employees, CH):
        n = min(CH, a.employees - lo)
        s.execute(insert(Employee), [{"id": lo + i + 1, "external_id": f"E{lo + i + 1}", "name": f"Employee {lo + i + 1}",
                  "department": f"Dept {random.randint(1, 40)}"} for i in range(n)])
        s.execute(insert(Rating), [{"employee_id": lo + i + 1, "skill_id": k, "level": random.randint(0, 5), "confidence": 0.6, "source": "seed"}
                  for i in range(n) for k in random.sample(range(1, a.skills + 1), a.ratings)])
        s.commit(); print(f"loaded {lo + n:,} employees", flush=True)
print(f"data load: {time.time() - t:.0f}s")
for r in range(1, a.roles + 1):
    t0 = time.time(); recompute_role(r); print(f"role {r}: readiness for all employees in {time.time() - t0:.1f}s", flush=True)
with SessionLocal() as s:
    print("readiness rows:", f"{s.scalar(select(func.count()).select_from(Readiness)):,}")
