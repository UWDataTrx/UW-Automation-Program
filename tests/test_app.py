import json
import os
import tkinter as tk

import pandas as pd
import pytest

from app import App, ConfigManager


@pytest.fixture
def tmp_work_dir(tmp_path, monkeypatch):
    """
    Create a temporary working directory and chdir into it, so that ConfigManager
    will create its config.json there.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_save_default_creates_config(tmp_work_dir):
    # When no config.json exists, ConfigManager.save_default() should create one
    # under the current directory (tmp_work_dir).
    cm = ConfigManager()
    config_path = tmp_work_dir / "config.json"

    assert config_path.exists(), "Config file was not created."
    with open(config_path, "r") as f:
        data = json.load(f)
    # By default, ConfigManager sets 'last_folder' to the cwd
    assert "last_folder" in data
    assert data["last_folder"] == str(tmp_work_dir)


def test_load_existing_config(tmp_work_dir):
    # Write a custom config.json, then ensure ConfigManager.load() honors it.
    config_path = tmp_work_dir / "config.json"
    custom = {"last_folder": "C:/some/path/xyz"}
    with open(config_path, "w") as f:
        json.dump(custom, f)

    cm = ConfigManager()
    assert (
        cm.config == custom
    ), "ConfigManager did not load the existing config.json correctly."


def test_filter_template_columns_extracts_correct_range():
    # Build a sample DataFrame where columns go: ['A','B','Client Name','X','Y','Logic','Z','W']
    df = pd.DataFrame(
        {
            "A": [1],
            "B": [2],
            "Client Name": ["foo"],
            "X": [3],
            "Y": [4],
            "Logic": [5],
            "Z": [6],
            "W": [7],
        }
    )

    # We only expect columns from 'Client Name' up through 'Logic' (inclusive).
    root = tk.Tk()
    root.withdraw()
    app = App(root)
    filtered = app.filter_template_columns(df)
    root.destroy()

    assert list(filtered.columns) == [
        "Client Name",
        "X",
        "Y",
        "Logic",
    ], f"Expected columns from 'Client Name' to 'Logic', got {list(filtered.columns)}"


def test_filter_template_columns_fallback_to_full_df_if_missing_logic():
    # If 'Client Name' or 'Logic' aren't found, it should return the full DataFrame unmodified
    df = pd.DataFrame({"Foo": [1, 2], "Bar": [3, 4]})

    root = tk.Tk()
    root.withdraw()
    app = App(root)
    result = app.filter_template_columns(df)
    root.destroy()

    # Since 'Client Name' or 'Logic' are not present, filter_template_columns should catch ValueError
    # and return the original DataFrame
    pd.testing.assert_frame_equal(result, df)


def test_format_dataframe_converts_datetimes_and_handles_na():
    # Build a DataFrame with one datetime column and one column containing a None
    orig = pd.DataFrame(
        {
            "dt1": [
                pd.to_datetime("2020-12-31 13:45:00"),
                pd.to_datetime("2021-01-01 00:00:00"),
            ],
            "value": [10, None],
        }
    )

    root = tk.Tk()
    root.withdraw()
    app = App(root)
    formatted = app.format_dataframe(orig)
    root.destroy()

    # 'dt1' should now be strings in format '%Y-%m-%d %H:%M:%S'
    assert formatted["dt1"].dtype == object
    assert formatted["dt1"].iloc[0] == "2020-12-31 13:45:00"
    assert formatted["dt1"].iloc[1] == "2021-01-01 00:00:00"

    # The None in 'value' should become an empty string
    assert formatted["value"].iloc[1] == ""


# (Optional) If you want to guard GUI‐dependent tests to skip automatically when no display is available:
def is_display_available():
    try:
        root = tk.Tk()
        root.destroy()
        return True
    except tk.TclError:
        return False


@pytest.mark.skipif(not is_display_available(), reason="Tkinter display not available")
def test_app_instantiation_and_basic_attributes():
    # A minimal smoke–test to ensure that App(root) does not crash immediately,
    # and that certain attributes exist.
    root = tk.Tk()
    root.withdraw()
    app = App(root)

    # Basic sanity checks:
    assert hasattr(app, "file1_path")
    assert hasattr(app, "file2_path")
    assert hasattr(app, "template_file_path")
    assert isinstance(app.progress_bar, type(app.progress_bar))

    root.destroy()
