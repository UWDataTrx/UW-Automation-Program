import pandas as pd
import numpy as np


def process_logic_block(df_block):
    arr = df_block.to_numpy()
    col_idx = {col: i for i, col in enumerate(df_block.columns)}
    qty = arr[:, col_idx["QUANTITY"]].astype(float)
    is_reversal = qty < 0
    is_claim = qty > 0
    ndc = arr[:, col_idx["NDC"]].astype(str)
    member = arr[:, col_idx["MemberID"]].astype(str)
    datefilled = pd.to_datetime(arr[:, col_idx["DATEFILLED"]], errors="coerce")
    abs_qty = np.abs(qty)
    if np.any(is_reversal):
        rev_idx = np.where(is_reversal)[0]
        claim_idx = (
            np.where(is_claim)[0] if np.any(is_claim) else np.array([], dtype=int)
        )
        for i in rev_idx:
            found_match = False
            if claim_idx.size > 0:
                matches = (
                    (ndc[claim_idx] == ndc[i])
                    & (member[claim_idx] == member[i])
                    & (abs_qty[claim_idx] == abs_qty[i])
                )
                date_diffs = np.abs((datefilled[claim_idx] - datefilled[i]).days)
                matches &= date_diffs <= 30
                if np.any(matches):
                    arr[i, col_idx["Logic"]] = "OR"
                    arr[claim_idx[matches][0], col_idx["Logic"]] = "OR"
                    found_match = True
            if not found_match:
                arr[i, col_idx["Logic"]] = "OR"
    return pd.DataFrame(arr, columns=df_block.columns)


def worker(df_block, out_queue):
    result = process_logic_block(df_block)
    out_queue.put(result)
