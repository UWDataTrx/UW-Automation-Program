import pandas as pd
import numpy as np
import sys
from pathlib import Path
# Ensure project root is in sys.path before importing project_settings
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
from project_settings import PROJECT_ROOT  # noqa: E402
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

def process_logic_block(df_block):
    """
    Vectorized numpy logic to mark 'OR' in 'Logic' for reversals with matching claims.
    Refactored to reduce nesting complexity and improve readability.
    """
    arr = df_block.to_numpy()
    col_idx = {col: i for i, col in enumerate(df_block.columns)}

    # Extract and prepare data
    logic_data = _extract_logic_data(arr, col_idx)

    # Early return if no reversals to process
    if not np.any(logic_data["is_reversal"]):
        return pd.DataFrame(arr, columns=df_block.columns)

    # Process reversals with reduced nesting
    _process_reversals(arr, col_idx, logic_data)

    return pd.DataFrame(arr, columns=df_block.columns)


def _extract_logic_data(arr, col_idx):
    """Extract and prepare data for logic processing."""
    qty = arr[:, col_idx["QUANTITY"]].astype(float)
    return {
        "qty": qty,
        "is_reversal": qty < 0,
        "is_claim": qty > 0,
        "ndc": arr[:, col_idx["NDC"]].astype(str),
        "member": arr[:, col_idx["MemberID"]].astype(str),
        "datefilled": pd.to_datetime(arr[:, col_idx["DATEFILLED"]], errors="coerce"),
        "abs_qty": np.abs(qty),
    }


def _process_reversals(arr, col_idx, logic_data):
    """Process reversals with matching logic, using guard clauses to reduce nesting."""
    rev_idx = np.where(logic_data["is_reversal"])[0]
    claim_idx = (
        np.where(logic_data["is_claim"])[0]
        if np.any(logic_data["is_claim"])
        else np.array([], dtype=int)
    )

    match_context = {
        "arr": arr,
        "col_idx": col_idx,
        "logic_data": logic_data,
        "claim_idx": claim_idx,
    }

    for i in rev_idx:
        found_match = _try_find_match(match_context, i)

        # Mark unmatched reversals as 'OR'
        if not found_match:
            arr[i, col_idx["Logic"]] = "OR"


def _try_find_match(match_context, reversal_idx):
    """Attempt to find a matching claim for a reversal. Returns True if match found."""
    arr = match_context["arr"]
    col_idx = match_context["col_idx"]
    logic_data = match_context["logic_data"]
    claim_idx = match_context["claim_idx"]

    # Guard clause: no claims to match against
    if claim_idx.size == 0:
        return False

    # Find potential matches
    matches = _find_matching_claims(logic_data, claim_idx, reversal_idx)

    # Guard clause: no matches found
    if not np.any(matches):
        return False

    # Select the best match (closest date)
    matching_claim_indices = claim_idx[matches]
    if len(matching_claim_indices) > 1:
        # Calculate date differences for all matches
        date_diffs = np.abs(
            (
                logic_data["datefilled"][matching_claim_indices]
                - logic_data["datefilled"][reversal_idx]
            ).days
        )
        # Select the match with the smallest date difference
        best_match_idx = matching_claim_indices[np.argmin(date_diffs)]
    else:
        best_match_idx = matching_claim_indices[0]

    # Mark both reversal and matching claim as 'OR'
    arr[reversal_idx, col_idx["Logic"]] = "OR"
    arr[best_match_idx, col_idx["Logic"]] = "OR"
    return True


def _find_matching_claims(logic_data, claim_idx, reversal_idx):
    """Find claims that match the reversal based on NDC, member, quantity, and date."""
    matches = (
        (logic_data["ndc"][claim_idx] == logic_data["ndc"][reversal_idx])
        & (logic_data["member"][claim_idx] == logic_data["member"][reversal_idx])
        & (logic_data["abs_qty"][claim_idx] == logic_data["abs_qty"][reversal_idx])
    )

    # Add date constraint (within 30 days)
    date_diffs = np.abs(
        (
            logic_data["datefilled"][claim_idx] - logic_data["datefilled"][reversal_idx]
        ).days
    )
    matches &= date_diffs <= 30

    return matches


def worker(df_block, out_queue):
    """Worker function for multiprocessing."""
    result = process_logic_block(df_block)
    out_queue.put(result)
