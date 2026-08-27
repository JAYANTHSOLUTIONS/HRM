"""
Standalone entrypoint so this module can be run/tested on its own.

======================================================================
HOW TO MERGE INTO THE REAL DAYFLOW APP
======================================================================
Your existing `main.py` (from Part 1/2) almost certainly already does:

    app = FastAPI(...)
    app.include_router(auth_router)
    app.include_router(admin_router)
    ...

Just add:

    from app.api.v1 import employee_module_router
    from app.core.exceptions import install_exception_handlers

    app.include_router(employee_module_router)
    install_exception_handlers(app)   # skip if Part 1/2 already installs
                                       # handlers for AppError-shaped errors

...and delete this file. Nothing else in Part 3 depends on how the app
object itself is constructed.
======================================================================
"""
from fastapi import FastAPI

from app.api.v1 import employee_module_router
from app.core.exceptions import install_exception_handlers

app = FastAPI(title="Dayflow HRMS — Employee Self-Service (Part 3)")

app.include_router(employee_module_router)
install_exception_handlers(app)


@app.get("/health")
def health():
    return {"status": "ok"}
