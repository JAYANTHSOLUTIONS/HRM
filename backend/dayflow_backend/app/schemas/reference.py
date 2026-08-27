from pydantic import BaseModel, ConfigDict


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    department_id: int
    department_name: str
    is_active: bool


class DepartmentCreate(BaseModel):
    department_name: str


class DepartmentUpdate(BaseModel):
    department_name: str | None = None
    is_active: bool | None = None


class DepartmentList(BaseModel):
    items: list[DepartmentOut]


class DesignationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    designation_id: int
    title: str
    is_active: bool


class DesignationCreate(BaseModel):
    title: str


class DesignationUpdate(BaseModel):
    title: str | None = None
    is_active: bool | None = None


class DesignationList(BaseModel):
    items: list[DesignationOut]
