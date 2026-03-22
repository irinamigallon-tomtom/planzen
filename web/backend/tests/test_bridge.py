"""
Tests for the bridge adapter layer.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from planzen.core_logic import CapacityConfig
from planzen.config import (
    COL_BUDGET_BUCKET, COL_EPIC, COL_ESTIMATION, COL_PRIORITY,
    OUT_COL_EPIC, OUT_COL_ESTIMATION, OUT_COL_BUDGET_BUCKET,
    OUT_COL_PRIORITY, OUT_COL_TOTAL_WEEKS, OUT_COL_OFF_ESTIMATE,
)
from bridge import (
    allocation_df_to_rows,
    capacity_config_from_model,
    capacity_config_to_model,
    epics_df_from_models,
)
from models import AllocationRow, CapacityConfigModel, EpicModel

import pandas as pd


class TestEpicsDfFromModels:
    def test_columns_correct(self):
        epics = [
            EpicModel(
                epic_description="Test Epic",
                estimation=5.0,
                budget_bucket="Engineering",
                priority=1.0,
            )
        ]
        df = epics_df_from_models(epics)
        assert COL_EPIC in df.columns
        assert COL_ESTIMATION in df.columns
        assert COL_BUDGET_BUCKET in df.columns
        assert COL_PRIORITY in df.columns

    def test_values_correct(self):
        epics = [
            EpicModel(
                epic_description="Epic A",
                estimation=3.5,
                budget_bucket="Bucket X",
                priority=2.0,
            )
        ]
        df = epics_df_from_models(epics)
        row = df.iloc[0]
        assert row[COL_EPIC] == "Epic A"
        assert row[COL_ESTIMATION] == 3.5
        assert row[COL_BUDGET_BUCKET] == "Bucket X"
        assert row[COL_PRIORITY] == 2.0

    def test_multiple_epics(self):
        epics = [
            EpicModel(epic_description=f"Epic {i}", estimation=float(i), budget_bucket="B", priority=float(i))
            for i in range(1, 4)
        ]
        df = epics_df_from_models(epics)
        assert len(df) == 3


class TestCapacityConfigFromModel:
    def test_scalar_fields(self):
        model = CapacityConfigModel(
            eng_bruto=8.0,
            eng_absence=0.5,
            mgmt_capacity=1.0,
            mgmt_absence=0.1,
        )
        config = capacity_config_from_model(model)
        assert config.num_engineers == 8.0
        assert config.num_managers == 1.0
        assert config.eng_absence_per_week == 0.5
        assert config.mgmt_absence_per_week == 0.1

    def test_per_week_dicts_empty_by_default(self):
        model = CapacityConfigModel(
            eng_bruto=5.0, eng_absence=0.2, mgmt_capacity=1.0, mgmt_absence=0.1
        )
        config = capacity_config_from_model(model)
        assert config.eng_bruto_by_week is None or config.eng_bruto_by_week == {}
        assert config.eng_absence_by_week is None or config.eng_absence_by_week == {}

    def test_per_week_dicts_converted(self):
        model = CapacityConfigModel(
            eng_bruto=5.0,
            eng_absence=0.2,
            mgmt_capacity=1.0,
            mgmt_absence=0.1,
            eng_bruto_by_week={"Mar.30": 6.0},
            eng_absence_by_week={"Mar.30": 0.3},
        )
        config = capacity_config_from_model(model)
        assert config.eng_bruto_by_week is not None
        assert config.eng_absence_by_week is not None
        # Keys should be date objects
        for key in config.eng_bruto_by_week:
            assert isinstance(key, date)


class TestCapacityConfigToModel:
    def test_roundtrip_scalars(self):
        model = CapacityConfigModel(
            eng_bruto=7.0,
            eng_absence=0.4,
            mgmt_capacity=1.5,
            mgmt_absence=0.2,
        )
        config = capacity_config_from_model(model)
        mondays = [date(2026, 3, 30)]
        result = capacity_config_to_model(config, mondays)
        assert result.eng_bruto == 7.0
        assert result.mgmt_capacity == 1.5
        assert result.eng_absence == 0.4
        assert result.mgmt_absence == 0.2

    def test_roundtrip_preserves_per_week(self):
        model = CapacityConfigModel(
            eng_bruto=5.0,
            eng_absence=0.2,
            mgmt_capacity=1.0,
            mgmt_absence=0.1,
            eng_bruto_by_week={"Mar.30": 6.0},
        )
        config = capacity_config_from_model(model)
        mondays = [date(2026, 3, 30)]
        result = capacity_config_to_model(config, mondays)
        assert "Mar.30" in result.eng_bruto_by_week
        assert result.eng_bruto_by_week["Mar.30"] == 6.0


class TestAllocationDfToRows:
    def _make_df(self):
        week_labels = ["Mar.30", "Apr.06"]
        rows = [
            {
                OUT_COL_BUDGET_BUCKET: "Eng",
                OUT_COL_EPIC: "Epic Alpha",
                OUT_COL_PRIORITY: 1.0,
                OUT_COL_ESTIMATION: 2.0,
                OUT_COL_TOTAL_WEEKS: 2.0,
                OUT_COL_OFF_ESTIMATE: False,
                "Mar.30": 1.0,
                "Apr.06": 1.0,
            }
        ]
        return pd.DataFrame(rows), week_labels

    def test_returns_allocation_rows(self):
        df, week_labels = self._make_df()
        result = allocation_df_to_rows(df, week_labels, week_labels)
        assert len(result) == 1
        assert isinstance(result[0], AllocationRow)

    def test_label_correct(self):
        df, week_labels = self._make_df()
        result = allocation_df_to_rows(df, week_labels, week_labels)
        assert result[0].label == "Epic Alpha"

    def test_week_values_present(self):
        df, week_labels = self._make_df()
        result = allocation_df_to_rows(df, week_labels, week_labels)
        assert "Mar.30" in result[0].week_values
        assert result[0].week_values["Mar.30"] == 1.0
        assert result[0].week_values["Apr.06"] == 1.0
