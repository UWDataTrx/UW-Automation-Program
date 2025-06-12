import pytest
from pathlib import Path
from merge import merge_files

def test_merge_files(tmp_path):
    file1 = tmp_path / "f1.csv"
    file2 = tmp_path / "f2.csv"
    file1.write_text("DATEFILLED,SOURCERECORDID\n2020-01-01,1")
    file2.write_text("SOURCERECORDID,Total AWP (Historical)\n1,50.0")
    merge_files(str(file1), str(file2))
    assert Path("merged_file.xlsx").exists()
