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

    def test_export_returns_xlsx(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.get(f"/api/sessions/{sid}/export")
        assert resp.status_code == 200, resp.text
        assert "spreadsheetml" in resp.headers["content-type"]

    def test_export_content_disposition(self, client, example_xlsx):
        session = self._upload(client, example_xlsx)
        sid = session["session_id"]
        resp = client.get(f"/api/sessions/{sid}/export")
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd
        assert "_formulas.xlsx" in cd
        assert "output_" in cd


# ---------------------------------------------------------------------------
# Upload sync tests: behaviours shared by CLI and web must match
# ---------------------------------------------------------------------------

def _make_xlsx(tmp_path, rows: list[dict], filename: str = "test.xlsx") -> Path:
    """Write a list of row dicts to a temp xlsx file."""
    import pandas as pd
    p = tmp_path / filename
    pd.DataFrame(rows).to_excel(p, index=False)
    return p


def _upload_xlsx(client, path: Path, quarter: int = 2):
    with open(path, "rb") as f:
        return client.post(
            "/api/sessions/upload",
            files={"file": (path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"quarter": str(quarter)},
        )


class TestUploadBehaviourSync:
    """
    Verify that behaviours added to excel_io.py (Priority imputation, unnamed
    column dropping, Budget Bucket filtering, per-week-only bruto) are active
    through the web upload path, keeping CLI and web in sync.
    """

    def test_priority_imputed_from_bucket_on_upload(self, client, tmp_path):
        """Upload a file with no Priority column; epics get Priority from BUCKET_PRIORITY."""
        from planzen.config import BUCKET_PRIORITY
        bucket = "Customer Support"
        rows = [
            {"Budget Bucket": "Engineer Capacity (Bruto)", "Epic Description": "Engineer Capacity (Bruto)", "Estimation": 3.0},
            {"Budget Bucket": bucket, "Epic Description": "Fix crash", "Estimation": 2.0},
        ]
        p = _make_xlsx(tmp_path, rows)
        resp = _upload_xlsx(client, p)
        assert resp.status_code == 200, resp.text
        epics = resp.json()["epics"]
        assert len(epics) == 1
        assert epics[0]["priority"] == float(BUCKET_PRIORITY[bucket])

    def test_unnamed_columns_silently_dropped_on_upload(self, client, tmp_path):
        """Unnamed headerless helper columns are dropped; upload succeeds."""
        import pandas as pd
        # Create file without column headers for some columns
        p = tmp_path / "unnamed.xlsx"
        df = pd.DataFrame([
            ["Engineer Capacity (Bruto)", "Engineer Capacity (Bruto)", 3.0, "helper value"],
            ["Customer Support", "Fix bug", 2.0, "another helper"],
        ], columns=["Budget Bucket", "Epic Description", "Estimation", None])
        df.to_excel(p, index=False)
        resp = _upload_xlsx(client, p)
        assert resp.status_code == 200, resp.text

    def test_annotation_rows_without_budget_bucket_dropped_on_upload(self, client, tmp_path):
        """Rows with Epic Description but no Budget Bucket are silently discarded."""
        rows = [
            {"Budget Bucket": "Engineer Capacity (Bruto)", "Epic Description": "Engineer Capacity (Bruto)", "Estimation": 3.0},
            {"Budget Bucket": "Customer Support", "Epic Description": "Real epic", "Estimation": 1.0, "Priority": 0},
            {"Budget Bucket": None, "Epic Description": "just a note", "Estimation": None},
        ]
        p = _make_xlsx(tmp_path, rows)
        resp = _upload_xlsx(client, p)
        assert resp.status_code == 200, resp.text
        epics = resp.json()["epics"]
        assert len(epics) == 1
        assert epics[0]["epic_description"] == "Real epic"

    def test_per_week_only_bruto_accepted_on_upload(self, client, tmp_path):
        """Engineer Capacity row with week-column values only (no scalar) uploads successfully."""
        from datetime import date, timedelta
        import pandas as pd
        q2_mondays = [date(2026, 3, 30) + timedelta(weeks=i) for i in range(13)]
        week_cols = [f"{m.day}.{m.month}." for m in q2_mondays]
        bruto_row: dict = {
            "Budget Bucket": "Engineer Capacity (Bruto)",
            "Epic Description": "Engineer Capacity (Bruto)",
            "Estimation": None,
        }
        for w in week_cols:
            bruto_row[w] = 2.0
        epic_row = {"Budget Bucket": "Customer Support", "Epic Description": "Fix bug", "Estimation": 1.0, "Priority": 0}
        p = _make_xlsx(tmp_path, [bruto_row, epic_row])
        resp = _upload_xlsx(client, p)
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["epics"]) == 1
