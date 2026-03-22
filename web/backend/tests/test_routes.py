"""
Integration tests for the planzen REST API routes.
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestSessionUpload:
    def test_upload_valid_file(self, client, example_xlsx):
        with open(example_xlsx, "rb") as f:
            resp = client.post(
                "/api/sessions/upload",
                files={"file": ("input_example.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"quarter": "2"},
            )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "session_id" in body
        assert body["session_id"]
        assert len(body["epics"]) > 0

    def test_upload_returns_quarter(self, client, example_xlsx):
        with open(example_xlsx, "rb") as f:
            resp = client.post(
                "/api/sessions/upload",
                files={"file": ("input_example.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"quarter": "2"},
            )
        assert resp.json()["quarter"] == 2


class TestSessionCRUD:
    def _upload(self, client, example_xlsx, quarter=2):
        with open(example_xlsx, "rb") as f:
            resp = client.post(
                "/api/sessions/upload",
                files={"file": ("input_example.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"quarter": str(quarter)},
            )
        assert resp.status_code == 200
        return resp.json()

    def test_get_session(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == sid

    def test_get_sessions_list(self, client, example_xlsx):
        self._upload(client, example_xlsx)
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        assert len(resp.json()) >= 1

    def test_update_capacity(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        new_capacity = {
            "eng_bruto": 10.0,
            "eng_absence": 1.0,
            "mgmt_capacity": 2.0,
            "mgmt_absence": 0.2,
            "eng_bruto_by_week": {},
            "eng_absence_by_week": {},
        }
        resp = client.put(f"/api/sessions/{sid}/capacity", json=new_capacity)
        assert resp.status_code == 200
        assert resp.json()["capacity"]["eng_bruto"] == 10.0

    def test_update_epics(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        new_epics = [
            {
                "epic_description": "New Epic",
                "estimation": 3.0,
                "budget_bucket": "Test",
                "priority": 1.0,
                "allocation_mode": "Sprint",
                "link": "",
                "type": "",
                "milestone": "",
            }
        ]
        resp = client.put(f"/api/sessions/{sid}/epics", json=new_epics)
        assert resp.status_code == 200
        assert resp.json()["epics"][0]["epic_description"] == "New Epic"

    def test_delete_session(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.delete(f"/api/sessions/{sid}")
        assert resp.status_code == 204
        # Subsequent GET returns 404
        resp = client.get(f"/api/sessions/{sid}")
        assert resp.status_code == 404

    def test_get_nonexistent_session_404(self, client):
        resp = client.get("/api/sessions/does-not-exist")
        assert resp.status_code == 404


class TestCompute:
    def _upload(self, client, example_xlsx):
        with open(example_xlsx, "rb") as f:
            resp = client.post(
                "/api/sessions/upload",
                files={"file": ("input_example.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"quarter": "2"},
            )
        assert resp.status_code == 200
        return resp.json()

    def test_compute_returns_rows(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.post(f"/api/sessions/{sid}/compute")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert len(body["rows"]) > 0

    def test_compute_has_week_labels(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.post(f"/api/sessions/{sid}/compute")
        body = resp.json()
        assert len(body["week_labels"]) >= 13

    def test_compute_session_id(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.post(f"/api/sessions/{sid}/compute")
        assert resp.json()["session_id"] == sid


class TestExport:
    def _upload(self, client, example_xlsx):
        with open(example_xlsx, "rb") as f:
            resp = client.post(
                "/api/sessions/upload",
                files={"file": ("input_example.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                data={"quarter": "2"},
            )
        assert resp.status_code == 200
        return resp.json()

    def test_export_returns_zip(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.get(f"/api/sessions/{sid}/export")
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"] == "application/zip"

    def test_export_content_disposition(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.get(f"/api/sessions/{sid}/export")
        assert "attachment" in resp.headers.get("content-disposition", "")
        assert ".zip" in resp.headers.get("content-disposition", "")
