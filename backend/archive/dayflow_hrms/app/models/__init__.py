"""
Importing this package registers every model (Part 1/2 stand-ins +
Part 3 models) on the SAME `Base.metadata`, which is what lets
Alembic autogenerate a correct migration and what lets SQLAlchemy
resolve the string-based relationship() references across files.
"""
from app.assumed_existing.auth import User, UserRole  # noqa: F401
from app.assumed_existing.org_models import (  # noqa: F401
    Department,
    Designation,
    Employee,
    EmploymentStatus,
    EmploymentType,
    Gender,
    SalaryComponent,
    SalaryComponentType,
    SalaryStructure,
    WageType,
)
from app.models.attendance import Attendance, AttendanceStatus  # noqa: F401
from app.models.document import Document  # noqa: F401
from app.models.leave import LeaveBalance, LeaveRequest, LeaveRequestStatus, LeaveType  # noqa: F401
from app.models.notification import Notification  # noqa: F401
