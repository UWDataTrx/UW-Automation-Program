"""
Logic processing utilities extracted from app.py
Following CodeScene ACE principles for better code organization
"""

import logging
import warnings
from dataclasses import dataclass
from typing import Dict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Filter out specific warnings
warnings.filterwarnings("ignore", category=FutureWarning, message=".*swapaxes.*")


@dataclass
class LogicData:
    """Data class to encapsulate logic processing data."""

    qty: np.ndarray
    is_reversal: np.ndarray
    is_claim: np.ndarray
    ndc: np.ndarray
    member: np.ndarray
    datefilled: pd.DatetimeIndex
    abs_qty: np.ndarray


@dataclass
class MatchContext:
    """Context object to encapsulate matching parameters."""

    arr: np.ndarray
    col_idx: Dict[str, int]
    logic_data: LogicData
    claim_idx: np.ndarray


class LogicProcessor:
    """Handles logic processing for reversal matching."""

    @staticmethod
    def process_logic_block(df_block: pd.DataFrame) -> pd.DataFrame:
        """
        Vectorized numpy logic to mark 'OR' in 'Logic' for reversals with matching claims.
        Refactored to reduce nesting complexity and improve readability.
        """
        arr = df_block.to_numpy()
        col_idx = {col: i for i, col in enumerate(df_block.columns)}

        # Extract and prepare data
        logic_data = LogicProcessor._extract_logic_data(arr, col_idx)

        # Early return if no reversals to process
        if not np.any(logic_data.is_reversal):
            return pd.DataFrame(arr, columns=df_block.columns)

        # Process reversals with reduced nesting
        LogicProcessor._process_reversals(arr, col_idx, logic_data)

        return pd.DataFrame(arr, columns=df_block.columns)

    @staticmethod
    def _extract_logic_data(arr: np.ndarray, col_idx: Dict[str, int]) -> LogicData:
        """Extract and prepare data for logic processing."""
        qty = arr[:, col_idx["QUANTITY"]].astype(float)

        return LogicData(
            qty=qty,
            is_reversal=qty < 0,
            is_claim=qty > 0,
            ndc=arr[:, col_idx["NDC"]].astype(str),
            member=arr[:, col_idx["MemberID"]].astype(str),
            datefilled=pd.to_datetime(arr[:, col_idx["DATEFILLED"]], errors="coerce"),
            abs_qty=np.abs(qty),
        )

    @staticmethod
    def _process_reversals(
        arr: np.ndarray, col_idx: Dict[str, int], logic_data: LogicData
    ):
        """Process reversals with matching logic, using guard clauses to reduce nesting."""
        rev_idx = np.where(logic_data.is_reversal)[0]
        claim_idx = (
            np.where(logic_data.is_claim)[0]
            if np.any(logic_data.is_claim)
            else np.array([], dtype=int)
        )

        # Create context object to reduce function argument count
        match_context = MatchContext(arr, col_idx, logic_data, claim_idx)

        for i in rev_idx:
            found_match = LogicProcessor._try_find_match(match_context, i)

            # Mark unmatched reversals as 'OR'
            if not found_match:
                arr[i, col_idx["Logic"]] = "OR"

    @staticmethod
    def _try_find_match(context: MatchContext, reversal_idx: int) -> bool:
        """Attempt to find a matching claim for a reversal. Returns True if match found."""
        # Guard clause: no claims to match against
        if context.claim_idx.size == 0:
            return False

        # Find potential matches
        matches = LogicProcessor._find_matching_claims(
            context.logic_data, context.claim_idx, reversal_idx
        )

        # Guard clause: no matches found
        if not np.any(matches):
            return False

        # Select the best match (closest date)
        matching_claim_indices = context.claim_idx[matches]
        if len(matching_claim_indices) > 1:
            # Calculate date differences for all matches
            date_diffs = np.abs(
                (context.logic_data.datefilled[matching_claim_indices] - 
                 context.logic_data.datefilled[reversal_idx]).days
            )
            # Select the match with the smallest date difference
            best_match_idx = matching_claim_indices[np.argmin(date_diffs)]
        else:
            best_match_idx = matching_claim_indices[0]

        # Mark both reversal and matching claim as 'OR'
        context.arr[reversal_idx, context.col_idx["Logic"]] = "OR"
        context.arr[best_match_idx, context.col_idx["Logic"]] = "OR"
        return True

    @staticmethod
    def _find_matching_claims(
        logic_data: LogicData, claim_idx: np.ndarray, reversal_idx: int
    ) -> np.ndarray:
        """Find claims that match the reversal based on NDC, member, quantity, and date."""
        matches = (
            (logic_data.ndc[claim_idx] == logic_data.ndc[reversal_idx])
            & (logic_data.member[claim_idx] == logic_data.member[reversal_idx])
            & (logic_data.abs_qty[claim_idx] == logic_data.abs_qty[reversal_idx])
        )

        # Add date constraint (within 30 days)
        try:
            date_diffs = np.abs(
                (
                    logic_data.datefilled[claim_idx]
                    - logic_data.datefilled[reversal_idx]
                ).days
            )
            matches &= date_diffs <= 30
        except Exception as e:
            logger.warning(f"Date filtering failed: {e}")
            # Continue without date constraint

        return matches


# Backwards compatibility functions
def process_logic_block(df_block: pd.DataFrame) -> pd.DataFrame:
    """Backwards compatibility wrapper."""
    return LogicProcessor.process_logic_block(df_block)
