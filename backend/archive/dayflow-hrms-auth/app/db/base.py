"""
Declarative base shared by every model in the project (Parts 1, 2, 3).

Part 2 and Part 3 modules MUST import `Base` from here (not create their
own DeclarativeBase) so that a single MetaData object is used for Alembic
autogeneration across the whole schema.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
