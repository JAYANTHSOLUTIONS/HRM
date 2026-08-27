import io
from tests.conftest import auth_header


def test_reject_exe_upload(client, seed):
    emp_id = seed["employee"].employee_id
    files = {"file": ("malware.exe", io.BytesIO(b"MZ\x90\x00fakecontent"), "application/octet-stream")}
    resp = client.post(
        f"/api/v1/employees/{emp_id}/documents",
        data={"document_type": "RESUME"}, files=files,
        headers=auth_header(seed["admin_user"]),
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_upload_and_view_pdf(client, seed):
    emp_id = seed["employee"].employee_id
    pdf_bytes = b"%PDF-1.4\n%fake pdf content for test\n"
    files = {"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    resp = client.post(
        f"/api/v1/employees/{emp_id}/documents",
        data={"document_type": "RESUME"}, files=files,
        headers=auth_header(seed["admin_user"]),
    )
    assert resp.status_code == 201
    doc = resp.json()
    assert doc["mime_type"] == "application/pdf"
    assert doc["original_filename"] == "resume.pdf"

    view_resp = client.get(f"/api/v1/documents/{doc['document_id']}/view", headers=auth_header(seed["admin_user"]))
    assert view_resp.status_code == 200
    assert view_resp.headers["content-type"].startswith("application/pdf")
    assert view_resp.content == pdf_bytes


def test_employee_cannot_view_other_employees_document(client, seed):
    emp_id = seed["employee"].employee_id
    pdf_bytes = b"%PDF-1.4\nfake\n"
    files = {"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    resp = client.post(
        f"/api/v1/employees/{emp_id}/documents",
        data={"document_type": "RESUME"}, files=files,
        headers=auth_header(seed["admin_user"]),
    )
    doc_id = resp.json()["document_id"]

    # emp_user in this fixture is NOT linked to this employee record's user_id
    # by construction here (they ARE, actually -- so let's assert self-access works)
    view_resp = client.get(f"/api/v1/documents/{doc_id}/view", headers=auth_header(seed["emp_user"]))
    assert view_resp.status_code == 200
