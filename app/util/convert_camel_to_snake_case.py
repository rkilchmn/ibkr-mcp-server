"""Snake case conversion utility functions."""
import re
from typing import Any

import pandas as pd


def camel_to_snake(name: str) -> str:
  """Convert camelCase string to snake_case.

  Args:
    name: camelCase string to convert.

  Returns:
    snake_case version of the input string.

  Examples:
    >>> camel_to_snake("secType")
    'sec_type'
    >>> camel_to_snake("primaryExchange")
    'primary_exchange'
    >>> camel_to_snake("conId")
    'con_id'

  """
  # Handle the pattern where an uppercase letter follows a lowercase letter
  # Insert underscore before it and lowercase it
  s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
  # Handle the pattern where an uppercase letter follows another uppercase
  # followed by lowercase (e.g., XMLHttpRequest)
  s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
  return s2.lower()


def convert_df_columns_to_snake_case(df: pd.DataFrame) -> pd.DataFrame:
  """Convert all DataFrame column names from camelCase to snake_case.

  Args:
    df: DataFrame with camelCase column names.

  Returns:
    DataFrame with snake_case column names.

  """
  df = df.copy()
  df.columns = [camel_to_snake(col) for col in df.columns]
  return df


def obj_to_dict_snake_case(obj: Any) -> dict[str, Any]:
  """Convert an object to a dictionary with snake_case keys.

  Args:
    obj: Object to convert (typically an ib_async Contract or similar).

  Returns:
    Dictionary with snake_case keys from the object's public attributes.

  """
  return {
    camel_to_snake(k): v
    for k, v in obj.__dict__.items()
    if not k.startswith("_")
  }
