import os

import pytest
from openpyxl import Workbook


@pytest.fixture(scope="session", autouse=True)
def create_dummy_excel():
    filename = "./_Rx Repricing_wf.xlsx"
    if not os.path.exists(filename):
        wb = Workbook()
        ws = wb.active
        ws.title = "Claims Table"
        ws.append(
            ["pharmacy_npi", "pharmacy_nabp", "pharmacy_id"]
        )  # add columns as needed
        ws.append([1234567890, "NABP123", "123"])  # add dummy data as needed
        wb.save(filename)
    yield
    # Optionally, remove the file after tests
    # os.remove(filename)
