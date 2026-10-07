"""Set-based, incremental readiness engine: one SQL statement per chunk, no per-row Python."""
import os
from datetime import datetime
from sqlalchemy import DateTime, and_, case, delete, func, literal, select, true
from .db import SessionLocal, insert_fn
from .models import Employee, Rating, Readiness, RoleSkillReq

MIN_STORE = float(os.getenv("MIN_STORE_SCORE", "0"))  # raise (e.g. 40) to cap role_readiness size at huge scale
COLS = ["employee_id", "role_id", "score", "gap_count", "updated_at"]


def _select(started, emp_filter, role_id=None):
    e, q, r = Employee, RoleSkillReq, Rating
    lvl = func.coalesce(r.level, 0)  # missing rating = level 0
    got = case((lvl < q.level, lvl), else_=q.level)
    score = func.sum(got * q.weight) * 100.0 / func.nullif(func.sum(q.level * q.weight), 0)
    gap = func.sum(case((lvl < q.level, 1), else_=0))
    on = (q.role_id == role_id) if role_id is not None else true()
    return (select(e.id, q.role_id, score, gap, literal(started, DateTime))
            .select_from(e).join(q, on).outerjoin(r, and_(r.employee_id == e.id, r.skill_id == q.skill_id))
            .where(emp_filter).group_by(e.id, q.role_id).having(score >= MIN_STORE))


def _write(session, sel):
    st = insert_fn()(Readiness).from_select(COLS, sel)
    st = st.on_conflict_do_update(index_elements=["employee_id", "role_id"],
                                  set_={c: st.excluded[c] for c in COLS[2:]})
    session.execute(st)


def recompute_employees(session, ids, batch=1000):
    """Call after ratings change. Recomputes every role for these employees."""
    ids = list(ids)
    for i in range(0, len(ids), batch):
        sub, started = ids[i:i + batch], datetime.utcnow()
        _write(session, _select(started, Employee.id.in_(sub)))
        session.execute(delete(Readiness).where(Readiness.employee_id.in_(sub), Readiness.updated_at < started))
        session.commit()


def recompute_role(role_id, chunk=50_000):
    """Call after a role's requirements change (run as a background job). Chunked by employee id range."""
    started = datetime.utcnow()
    with SessionLocal() as s:
        max_id = s.scalar(select(func.max(Employee.id))) or 0
    for lo in range(0, max_id + 1, chunk):
        with SessionLocal() as s:
            _write(s, _select(started, and_(Employee.id >= lo, Employee.id < lo + chunk), role_id))
            s.commit()
    with SessionLocal() as s:
        s.execute(delete(Readiness).where(Readiness.role_id == role_id, Readiness.updated_at < started))
        s.commit()
