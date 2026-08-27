from app.models.notification import Notification


def test_list_my_notifications(client, db_session, auth_headers, seed_employee):
    db_session.add(
        Notification(user_id=seed_employee["user"].user_id, title="Leave approved", message="Enjoy!")
    )
    db_session.commit()

    resp = client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["unread_count"] == 1
    assert body["items"][0]["title"] == "Leave approved"


def test_mark_notification_read(client, db_session, auth_headers, seed_employee):
    notif = Notification(user_id=seed_employee["user"].user_id, title="x", message="y")
    db_session.add(notif)
    db_session.commit()

    resp = client.patch(f"/api/v1/notifications/{notif.notification_id}/read", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True


def test_cannot_mark_another_users_notification_read(
    client, db_session, auth_headers_second, seed_employee, seed_second_employee
):
    notif = Notification(user_id=seed_employee["user"].user_id, title="x", message="y")
    db_session.add(notif)
    db_session.commit()

    resp = client.patch(
        f"/api/v1/notifications/{notif.notification_id}/read", headers=auth_headers_second
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


def test_dashboard_aggregates_own_data_only(client, auth_headers, seed_employee):
    resp = client.get("/api/v1/dashboard/me", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["full_name"] == "Asha Singh"
    assert body["leave_balance_summary"][0]["leave_type"] == "Paid Leave"
    assert body["current_leave"] is None
