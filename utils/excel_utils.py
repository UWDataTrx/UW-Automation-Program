import os
import shutil
import logging
import xlwings as xw
import importlib.util
from typing import Any, Tuple
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# COM fallback via pywin32
EXCEL_COM_AVAILABLE = importlib.util.find_spec("win32com.client") is not None


def open_workbook(path: str, visible: bool = False) -> Tuple[Any, Any, bool]:
    """
    Open workbook via xlwings or COM fallback.
    Returns (wb, app_obj, use_com).
    """
    import time

    max_retries = 3
    delay = 2
    last_exc = None
    for attempt in range(max_retries):
        try:
            app = xw.App(visible=visible, add_book=False)  # Ensure no new book is added
            try:
                wb = app.books.open(path)
            except TypeError:
                # Try with password if provided in path (e.g., path='file.xlsx::password')
                if "::" in path:
                    file_path, password = path.split("::", 1)
                    wb = app.books.open(file_path, password=password)
                else:
                    raise
            return wb, app, False
        except Exception as e:
            last_exc = e
            logger.warning(
                f"Failed to open workbook (attempt {attempt + 1}/{max_retries}): {e}"
            )
            time.sleep(delay)
    if EXCEL_COM_AVAILABLE:
        import win32com.client as win32

        excel: Any = win32.Dispatch("Excel.Application")
        excel.Visible = visible  # Ensure Excel remains hidden
        excel.DisplayAlerts = False  # Suppress alerts
        try:
            if "::" in path:
                file_path, password = path.split("::", 1)
                wb: Any = excel.Workbooks.Open(
                    os.path.abspath(file_path), False, False, None, password
                )
            else:
                wb: Any = excel.Workbooks.Open(os.path.abspath(path))
        except Exception as e:
            logger.error(f"COM fallback failed to open workbook: {e}")
            raise
        return wb, excel, True
    logger.error(f"Failed to open workbook after {max_retries} attempts: {last_exc}")
    if last_exc is not None:
        raise last_exc
    # Should never reach here, but raise as a safeguard
    raise RuntimeError("Failed to open workbook and no exception was captured.")


def write_df_to_sheet_async(
    path: str,
    sheet_name: str,
    df: pd.DataFrame,
    start_cell: str = "A2",
    header: bool = False,
    index: bool = False,
    clear: bool = True,
    visible: bool = False,
    clear_by_label: bool = False,
    max_workers: int = 4,
) -> None:
    """
    Async version of write_df_to_sheet for large DataFrames (xlwings only).
    Splits DataFrame into row blocks and writes in parallel threads.
    """
    logger.info(
        f"[ASYNC] Writing to {path} in sheet '{sheet_name}' from cell {start_cell} with {max_workers} workers"
    )
    wb, app, use_com = open_workbook(path, visible)
    if use_com:
        # COM automation is not thread-safe; fallback to sync
        logger.warning("COM fallback does not support async writes. Using sync write.")
        return write_df_to_sheet(
            path,
            sheet_name,
            df,
            start_cell,
            header,
            index,
            clear,
            visible,
            clear_by_label,
        )
    try:
        ws = wb.sheets[sheet_name]
        cell = ws.range(start_cell)
    except Exception as e:
        close_workbook(wb, app, save=False, use_com=use_com)
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook.") from e

    start_row = cell.row
    start_col = cell.column
    n_rows, n_cols = df.shape
    total_rows = n_rows + (1 if header else 0)
    end_row = start_row + total_rows - 1
    end_col = start_col + n_cols - 1

    # Optionally clear before writing
    target = ws.range((start_row, start_col), (end_row, end_col))
    if clear:
        if clear_by_label:
            for idx, col in enumerate(df.columns, start_col):
                col_range = ws.range((start_row, idx), (end_row, idx))
                col_range.clear_contents()
        else:
            target.clear_contents()

    # Write header if needed
    if header:
        for j, h in enumerate(df.columns, start_col):
            ws.Cells(start_row, j).Value = h
        data_start = start_row + 1
    else:
        data_start = start_row

    # Split DataFrame into blocks for parallel writing
    block_size = max(100, n_rows // max_workers)
    blocks = [(i, min(i + block_size, n_rows)) for i in range(0, n_rows, block_size)]

    def write_block(start, stop):
        for i, row in enumerate(df.values[start:stop], data_start + start):
            for j, val in enumerate(row, start_col):
                ws.Cells(i, j).Value = val

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(write_block, start, stop) for start, stop in blocks]
        for f in as_completed(futures):
            f.result()

    close_workbook(wb, app, save=True, use_com=use_com)


def close_workbook(
    wb: Any, app_obj: Any, save: bool = True, use_com: bool = False
) -> None:
    """
    Close the workbook and quit the application.
    """
    if not use_com:
        if save:
            wb.save()
        wb.close()
        app_obj.quit()
    else:
        if save:
            wb.Save()
        wb.Close(SaveChanges=save)
        app_obj.Quit()


def write_df_to_sheet(
    path: str,
    sheet_name: str,
    df: pd.DataFrame,
    start_cell: str = "A2",
    header: bool = False,
    index: bool = False,
    clear: bool = True,
    visible: bool = False,
    clear_by_label: bool = False,
) -> None:
    """
    Write DataFrame to an Excel sheet without removing any formatting.
    Only clears the cells where values will be written.
    """
    logger.info(f"Writing to {path} in sheet '{sheet_name}' from cell {start_cell}")

    wb, app, use_com = open_workbook(path, visible)

    try:
        if not use_com:
            ws = wb.sheets[sheet_name]
            cell = ws.range(start_cell)

            def clear_func(rng):
                rng.clear_contents()
        else:
            ws: Any = wb.Worksheets(sheet_name)
            cell: Any = ws.Range(start_cell)

            def clear_func(rng):
                rng.ClearContents()
    except Exception as e:
        close_workbook(wb, app, save=False, use_com=use_com)
        raise ValueError(f"Sheet '{sheet_name}' not found in workbook.") from e

    # Determine start row/col and target range
    start_row = cell.row if not use_com else cell.Row
    start_col = cell.column if not use_com else cell.Column
    n_rows, n_cols = df.shape
    total_rows = n_rows + (1 if header else 0)
    end_row = start_row + total_rows - 1
    end_col = start_col + n_cols - 1

    if not use_com:
        target = ws.range((start_row, start_col), (end_row, end_col))
        if clear:
            if clear_by_label:
                # Clear by column label (header row)
                for idx, col in enumerate(df.columns, start_col):
                    col_range = ws.range((start_row, idx), (end_row, idx))
                    col_range.clear_contents()
            else:
                clear_func(target)
        target.options(index=index, header=header).value = df
    else:
        target = ws.Range(ws.Cells(start_row, start_col), ws.Cells(end_row, end_col))
        if clear:
            if clear_by_label:
                # Clear by column label (header row)
                for idx, col in enumerate(df.columns, start_col):
                    col_rng = ws.Range(ws.Cells(start_row, idx), ws.Cells(end_row, idx))
                    col_rng.ClearContents()
            else:
                clear_func(target)
        data_start = start_row
        if header:
            for j, h in enumerate(df.columns, start_col):
                ws.Cells(start_row, j).Value = h
            data_start += 1
        for i, row in enumerate(df.values.tolist(), data_start):
            for j, val in enumerate(row, start_col):
                ws.Cells(i, j).Value = val

    close_workbook(wb, app, save=True, use_com=use_com)


def write_df_to_template(
    template_path: str,
    output_path: str,
    sheet_name: str,
    df: pd.DataFrame,
    start_cell: str = "A2",
    header: bool = False,
    index: bool = False,
    visible: bool = False,
    open_file: bool = False,
) -> None:
    """
    Copy an Excel template and write a DataFrame into it without altering
    any existing formatting, charts, tables, or objects.

    If open_file is True, launch the filled workbook in Excel after writing.
    """
    shutil.copy(template_path, output_path)
    write_df_to_sheet(
        path=output_path,
        sheet_name=sheet_name,
        df=df,
        start_cell=start_cell,
        header=header,
        index=index,
        clear=True,
        visible=visible,
    )
    if open_file:
        os.startfile(output_path)
