"""Skills, roles and requirements are ROWS, so new skills/roles never need schema or code changes."""
from datetime import datetime
from sqlalchemy import (Boolean, BigInteger, DateTime, Float, ForeignKey, Index, Integer, SmallInteger, String, Text, desc)
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

BigPK = BigInteger().with_variant(Integer(), "sqlite")
now = datetime.utcnow


class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str | None] = mapped_column(String(80))
    taxonomy_ref: Mapped[str | None] = mapped_column(String(120))  # e.g. ESCO / O*NET id


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)  # succession-planning scope


class RoleSkillReq(Base):
    __tablename__ = "role_skill_requirements"
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger)  # required proficiency 0-5
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    __table_args__ = (Index("ix_req_skill", "skill_id"),)


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True)  # HRIS id
    name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(120))
    title: Mapped[str | None] = mapped_column(String(160))
    current_role_id: Mapped[int | None] = mapped_column(ForeignKey("roles.id"))
    availability: Mapped[int] = mapped_column(SmallInteger, default=100)  # % capacity free for new work
    __table_args__ = (Index("ix_emp_dept", "department", "id"), Index("ix_emp_role", "current_role_id"))


class Rating(Base):
    """Sparse current proficiency: a row exists only for skills with evidence. Partition by hash(employee_id) at scale."""
    __tablename__ = "employee_skill_ratings"
    employee_id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    source: Mapped[str] = mapped_column(String(30), default="manual")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (Index("ix_rating_skill_level", "skill_id", "level"),)


class Assessment(Base):
    """Append-only event log for audit and trend analysis."""
    __tablename__ = "assessments"
    id: Mapped[int] = mapped_column(BigPK, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigPK, index=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"))
    level: Mapped[int] = mapped_column(SmallInteger)
    score: Mapped[float | None] = mapped_column(Float)
    confidence: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(30))
    summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class Readiness(Base):
    """Precomputed employee x role fit (0-100). Never computed per request."""
    __tablename__ = "role_readiness"
    employee_id: Mapped[int] = mapped_column(BigPK, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    score: Mapped[float] = mapped_column(Float)
    gap_count: Mapped[int] = mapped_column(SmallInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    __table_args__ = (Index("ix_ready_role_score", "role_id", desc("score"), "employee_id"),)


class SkillDemand(Base):
    __tablename__ = "skill_demand"
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    target_headcount: Mapped[int] = mapped_column(Integer)


class Question(Base):
    """LLM-generated questions are cached per skill+level and reused across everyone (cost control)."""
    __tablename__ = "question_bank"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str] = mapped_column(Text)


class LearningResource(Base):
    """Learning catalog: each resource takes a learner TO `level` in a skill."""
    __tablename__ = "learning_resources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    provider: Mapped[str | None] = mapped_column(String(100))
    level: Mapped[int] = mapped_column(SmallInteger)
    hours: Mapped[int] = mapped_column(Integer)
    url: Mapped[str | None] = mapped_column(String(500))


class Project(Base):
    """Business demand: a project/initiative that needs a set of skills (resource optimisation)."""
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    description: Mapped[str | None] = mapped_column(Text)


class ProjectSkill(Base):
    __tablename__ = "project_skills"
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.id"), primary_key=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
