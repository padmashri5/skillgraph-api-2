"""Populate a realistic demo workspace:  python -m scripts.demo   (run once on an empty database)"""
import random
from sqlalchemy import func, insert, select
from app.db import Base, SessionLocal, engine
from app.models import (Employee, LearningResource, Project, ProjectSkill, Rating, Role, RoleSkillReq, Skill, SkillDemand)
from app.readiness import recompute_role

random.seed(7); Base.metadata.create_all(engine)
SKILLS = {"Python": "Engineering", "SQL": "Data", "Data Analysis": "Data", "Machine Learning": "Data", "Data Engineering": "Data",
          "Cloud Architecture": "Engineering", "DevOps": "Engineering", "Cybersecurity": "Security", "Software Design": "Engineering",
          "Communication": "Leadership", "Project Management": "Leadership", "Stakeholder Management": "Leadership",
          "Leadership": "Leadership", "Coaching": "Leadership", "Product Strategy": "Product", "Agile Delivery": "Product"}
ROLES = {  # name: (critical, {skill: level})
    "Data Scientist": (False, {"Python": 4, "SQL": 3, "Data Analysis": 4, "Machine Learning": 4, "Communication": 3}),
    "Cloud Engineer": (False, {"Python": 3, "Cloud Architecture": 4, "DevOps": 4, "Cybersecurity": 3, "Software Design": 3}),
    "Product Manager": (False, {"Product Strategy": 4, "Stakeholder Management": 4, "Communication": 4, "Agile Delivery": 3, "Data Analysis": 3}),
    "Security Analyst": (False, {"Cybersecurity": 4, "Cloud Architecture": 3, "DevOps": 3, "Communication": 3}),
    "Engineering Manager": (True, {"Leadership": 4, "Coaching": 4, "Software Design": 4, "Project Management": 4, "Stakeholder Management": 4, "Cloud Architecture": 3}),
    "Head of Data Platform": (True, {"Data Engineering": 5, "Leadership": 4, "Cloud Architecture": 4, "SQL": 4, "Stakeholder Management": 4, "Coaching": 3}),
}
FIRST = "Aisha Rohan Priya Karthik Meera Vikram Neha Arjun Sana Dev Ishaan Kavya Rahul Anjali Nikhil Divya Aditya Pooja Sameer Tara".split()
LAST = "Rao Mehta Nair Iyer Das Shah Kapoor Pillai Gupta Reddy Sharma Menon Joshi Bose Verma Singh Patel Kulkarni Nambiar Chopra".split()
DEPTS = ["Platform", "Data & AI", "Security", "Product", "Cloud Ops"]
clamp = lambda v: max(0, min(5, v))

with SessionLocal() as s:
    if s.scalar(select(func.count()).select_from(Skill)):
        raise SystemExit("Database already has data; use an empty database.")
    sid = {n: i for i, n in enumerate(SKILLS, 1)}
    s.execute(insert(Skill), [{"id": sid[n], "name": n, "category": c} for n, c in SKILLS.items()])
    rid = {n: i for i, n in enumerate(ROLES, 1)}
    s.execute(insert(Role), [{"id": rid[n], "name": n, "version": 1, "is_critical": c} for n, (c, _) in ROLES.items()])
    s.execute(insert(RoleSkillReq), [{"role_id": rid[n], "skill_id": sid[k], "level": v, "weight": 1.0} for n, (_, q) in ROLES.items() for k, v in q.items()])
    emps, ratings, normal = [], [], [n for n, (c, _) in ROLES.items() if not c]
    crit_slots = ["Engineering Manager"] * 6 + ["Head of Data Platform"] * 4
    for i in range(1, 421):
        if i <= len(crit_slots): role = crit_slots[i - 1]
        elif i <= len(crit_slots) + 14: role = None  # high-potential successors for critical roles
        else: role = random.choice(normal)
        hp = role is None
        target = random.choice(["Engineering Manager", "Head of Data Platform"]) if hp else role
        emps.append({"id": i, "external_id": f"E{i:04d}", "name": f"{random.choice(FIRST)} {random.choice(LAST)}",
                     "department": random.choice(DEPTS), "title": role or "Senior Engineer", "current_role_id": rid[role] if role else None,
                     "availability": random.choice([100, 100, 60, 30, 0])})
        have = {}
        for k, v in ROLES[target][1].items():
            have[k] = clamp(v + (random.randint(-1, 0) if hp else random.randint(-2, 1)))
        for k in random.sample(list(SKILLS), 3): have.setdefault(k, random.randint(1, 3))
        ratings += [{"employee_id": i, "skill_id": sid[k], "level": v, "confidence": round(random.uniform(.5, .95), 2), "source": random.choice(["hris_inference", "manual", "ai_assessment"])} for k, v in have.items() if v > 0]
    s.execute(insert(Employee), emps); s.execute(insert(Rating), ratings)
    courses = [(2, "Foundations of", 12), (3, "Applied", 24), (4, "Advanced", 32), (5, "Expert practice in", 40)]
    res = [{"skill_id": sid[n], "title": f"{t} {n}", "provider": random.choice(["Coursera", "Udemy", "Internal Academy", "LinkedIn Learning"]),
            "level": l, "hours": h, "url": "https://example.com/learn"} for n in SKILLS for l, t, h in courses]
    s.execute(insert(LearningResource), res)
    s.execute(insert(SkillDemand), [{"skill_id": sid[n], "target_headcount": random.randint(8, 40)} for n in SKILLS])
    projs = {"Customer 360 Platform": {"Data Engineering": 4, "SQL": 4, "Cloud Architecture": 3, "Python": 3},
             "Fraud Detection Model": {"Machine Learning": 4, "Python": 4, "Data Analysis": 3},
             "Zero-Trust Rollout": {"Cybersecurity": 4, "DevOps": 3, "Cloud Architecture": 3}}
    for i, (n, q) in enumerate(projs.items(), 1):
        s.execute(insert(Project), [{"id": i, "name": n, "description": "Demo initiative"}])
        s.execute(insert(ProjectSkill), [{"project_id": i, "skill_id": sid[k], "level": v, "weight": 1.0} for k, v in q.items()])
    s.commit()
for r in rid.values(): recompute_role(r)
print("Demo ready: 420 employees, 16 skills, 6 roles (2 critical), 3 projects, 64 courses")
