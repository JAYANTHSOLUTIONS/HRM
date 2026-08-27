import io


def _fake_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n%fake-pdf-for-tests\n" + b"0" * 100


def _fake_png_bytes() -> bytes:
    return b"\x89PNG\r\n\x1a\n" + b"0" * 100


def test_upload_and_list_my_documents(client, auth_headers):
    files = {"file": ("payslip.pdf", io.BytesIO(_fake_pdf_bytes()), "application/pdf")}
    resp = client.post(
        "/api/v1/employees/me/documents",
        headers=auth_headers,
        data={"document_type": "PAYSLIP"},
        files=files,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mime_type"] == "application/pdf"
    assert body["view_url"].endswith(f"/api/v1/documents/{body['document_id']}/view")

    listing = client.get("/api/v1/employees/me/documents", headers=auth_headers)
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == 1


def test_view_and_download_own_document(client, auth_headers):
    files = {"file": ("id.png", io.BytesIO(_fake_png_bytes()), "image/png")}
    uploaded = client.post(
        "/api/v1/employees/me/documents",
        headers=auth_headers,
        data={"document_type": "ID_PROOF"},
        files=files,
    ).json()

    view = client.get(f"/api/v1/documents/{uploaded['document_id']}/view", headers=auth_headers)
    assert view.status_code == 200
    assert view.headers["content-type"] == "image/png"
    assert "inline" in view.headers["content-disposition"]

    download = client.get(f"/api/v1/documents/{uploaded['document_id']}/download", headers=auth_headers)
    assert download.status_code == 200
    assert "attachment" in download.headers["content-disposition"]


def test_cannot_view_another_employees_document(client, auth_headers, auth_headers_second):
    files = {"file": ("id.png", io.BytesIO(_fake_png_bytes()), "image/png")}
    uploaded = client.post(
        "/api/v1/employees/me/documents",
        headers=auth_headers,
        data={"document_type": "ID_PROOF"},
        files=files,
    ).json()

    resp = client.get(f"/api/v1/documents/{uploaded['document_id']}/view", headers=auth_headers_second)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_disguised_executable_is_rejected(client, auth_headers):
    fake = io.BytesIO(b"MZ\x90\x00" + b"0" * 100)  # PE/EXE signature
    files = {"file": ("totally-a-photo.png", fake, "image/png")}
    resp = client.post(
        "/api/v1/employees/me/documents",
        headers=auth_headers,
        data={"document_type": "ID_PROOF"},
        files=files,
    )
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_profile_picture_upload_and_view(client, auth_headers):
    files = {"file": ("avatar.png", io.BytesIO(_fake_png_bytes()), "image/png")}
    resp = client.post("/api/v1/employees/me/profile-picture", headers=auth_headers, files=files)
    assert resp.status_code == 200
    assert resp.json()["profile_picture_url"] is not None

    view = client.get("/api/v1/employees/me/profile-picture/view", headers=auth_headers)
    assert view.status_code == 200
    assert view.headers["content-type"] == "image/png"


def test_profile_picture_rejects_non_image_document(client, auth_headers):
    files = {"file": ("resume.pdf", io.BytesIO(_fake_pdf_bytes()), "application/pdf")}
    resp = client.post("/api/v1/employees/me/profile-picture", headers=auth_headers, files=files)
    assert resp.status_code == 415
