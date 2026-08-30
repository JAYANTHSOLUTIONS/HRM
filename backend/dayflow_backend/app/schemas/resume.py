from pydantic import BaseModel, ConfigDict

class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    employee_id: int
    about: str | None = None
    what_i_love: str | None = None
    interests: str | None = None
    skills: list[str] | None = None
    certifications: list[dict] | None = None

class ResumeUpdate(BaseModel):
    about: str | None = None
    what_i_love: str | None = None
    interests: str | None = None
    skills: list[str] | None = None
    certifications: list[dict] | None = None
