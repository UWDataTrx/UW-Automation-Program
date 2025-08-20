import importlib.util
import logging
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Tuple, Union

import pandas as pd
import xlwings as xw

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

# COM fallback via pywin32
EXCEL_COM_AVAILABLE = importlib.util.find_spec("win32com.client") is not None


def validate_excel_file(file_path: Union[str, Path]) -> bool:
    """
    Validate if an Excel file is not corrupted and can be opened.
    Returns True if valid, False if corrupted.
    """
    try:
        # Quick validation using pandas first
        pd.read_excel(str(file_path), nrows=1)
        return True
    except Exception as e:
        logger.warning(f"Excel file validation failed for {file_path}: {e}")
        return False


def safe_excel_write(df: pd.DataFrame, output_path: Union[str, Path], **kwargs) -> bool:
    """
    Safely write DataFrame to Excel with atomic operations and validation.
    Returns True if successful, False otherwise.
    """
    try:
        output_path = Path(output_path)
        # Create a temporary file first
        temp_dir = output_path.parent
        with tempfile.NamedTemporaryFile(
            suffix=".xlsx", dir=temp_dir, delete=False
        ) as temp_file:
            temp_path = Path(temp_file.name)

        # Write to temporary file first
        df.to_excel(str(temp_path), **kwargs)

        # Validate the temporary file
        if not validate_excel_file(temp_path):
            temp_path.unlink(missing_ok=True)
            logger.error(f"Generated Excel file failed validation: {temp_path}")
            return False

        # If output file exists, create backup
        if output_path.exists():
            backup_path = output_path.with_suffix(output_path.suffix + ".backup")
            shutil.copy2(str(output_path), str(backup_path))
            logger.info(f"Created backup: {backup_path}")

        # Atomic move from temp to final location
        shutil.move(str(temp_path), str(output_path))
        logger.info(f"Successfully wrote Excel file: {output_path}")
        return True

    except Exception as e:
        logger.error(f"Safe Excel write failed: {e}")
        # Clean up temp file if it exists
        temp_path_to_clean = locals().get("temp_path")
        if temp_path_to_clean and Path(temp_path_to_clean).exists():
            try:
                Path(temp_path_to_clean).unlink(missing_ok=True)
            except Exception:
                pass
        return False


def check_disk_space(path: Union[str, Path], required_mb: int = 100) -> bool:
    """
    Check if there's sufficient disk space for Excel operations.
    """
    try:
        path = Path(path)
        stat = shutil.disk_usage(str(path))
        free_mb = stat.free / (1024 * 1024)
        if free_mb < required_mb:
            logger.warning(
                f"Low disk space: {free_mb:.1f}MB available, {required_mb}MB required"
            )
            return False
        return True
    except Exception as e:
        logger.warning(f"Could not check disk space: {e}")
        return True  # Assume OK if we can't check


def open_workbook(
    path: Union[str, Path], visible: bool = False
) -> Tuple[Any, Any, bool]:
    """
    Open workbook via xlwings or COM fallback.
    Returns (wb, app_obj, use_com).
    """
    import time

    max_retries = 3
    delay = 2
    last_exc = None
    path = str(path)
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
                    str(Path(file_path).resolve()), False, False, None, password
                )
            else:
                wb: Any = excel.Workbooks.Open(str(Path(path).resolve()))
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
    path: Union[str, Path],
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
    path: Union[str, Path],
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
            sheet_names = [s.name for s in wb.sheets]
            if sheet_name not in sheet_names:
                print(f"DEBUG: Available sheets in '{path}': {sheet_names}")
                raise ValueError(f"Sheet '{sheet_name}' not found in workbook. Available sheets: {sheet_names}")
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
    template_path: Union[str, Path],
    output_path: Union[str, Path],
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
    template_path = Path(template_path)
    output_path = Path(output_path)  # Use the provided output_path

    # Remove these hardcoded lines:
    # working_dir
    # output_name = "_Rx Repricing_wf.xlsx"
    # output_path = working_dir / output_name
    # Overwrite protection for key templates
    protected_templates = [
        "SHARx Blind Repricing 7.25.xlsx",
        "SHARx Standard Repricing 7.25.xlsx",
        "Template_Rx Claims for SHARx.xlsx",
        "Blind Repricing 7.25.xlsx",
        "Standard Repricing 7.25.xlsx",
    ]
    # Only create a copy if the output name is a protected template or matches the template path
    if (
        output_path.name in protected_templates
        or output_path.resolve() == template_path.resolve()
    ):
        base = output_path.stem
        suffix = output_path.suffix
        copy_name = f"{base}_copy{suffix}"
        copy_path = output_path.parent / copy_name
        i = 1
        while copy_path.exists():
            copy_name = f"{base}_copy{i}{suffix}"
            copy_path = output_path.parent / copy_name
            i += 1
        logger.warning(
            f"Output path '{output_path.name}' is a protected template or matches the template path. Writing to copy: {copy_path.name}"
        )
        output_path = copy_path
        # Diagnostic logging before writing to template
        logger.info(
            f"Writing {len(df)} rows and {df.shape[1]} columns to template at '{output_path}' (sheet: '{sheet_name}', cell: '{start_cell}')"
        )
    # If output_path is '_Rx Repricing_wf.xlsx' in working dir, allow overwrite; else, create new copy as above
    # (No extra logic needed, as above already handles protected/template cases)
    shutil.copy(str(template_path), str(output_path))
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
        try:
            output_path_str = str(output_path)
            import os

            if hasattr(os, "startfile"):
                os.startfile(output_path_str)
            else:
                import subprocess

                subprocess.run(["open", output_path_str])
        except Exception as e:
            logger.warning(f"Could not open file after writing: {e}")
