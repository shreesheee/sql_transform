import streamlit as st
import re

def transform_sql_expression(calculation):
    # Handling complete expression transformations first
    calculation = re.sub(r"CONVERT\s*\(\s*VARCHAR\s*,\s*GETDATE\s*\(\s*\)\s*,\s*112\s*\)", r"TO_CHAR(CURRENT_DATE, 'YYYYMMDD')", calculation, flags=re.IGNORECASE)

    calculation = re.sub(r"CONVERT\s*\(\s*DATETIME\s*,\s*'([^']+)'\s*,\s*120\s*\)", r"TO_TIMESTAMP_NTZ('\1', 'YYYY-MM-DD HH24:MI:SS')", calculation, flags=re.IGNORECASE)

    calculation = re.sub(r"FORMAT\(GETDATE\(\), 'yyyy-MM-dd HH:mm:ss'\)", "TO_CHAR(CURRENT_TIMESTAMP(), 'YYYY-MM-DD HH24:MI:SS')", calculation, flags=re.IGNORECASE)

    # Replaces + with ||
    calculation = re.sub(
    r'(\s*"[^"]*"\s*|\s*\'[^\']*\'\s*|\s*\w+\s*|\s*\w+\s*\([^)]*\)\s*)\s*\+\s*',
    lambda m: f'{m.group(1).replace(" ", "") if "\"" in m.group(1) else m.group(1).strip()} || ',
    calculation,
    flags=re.IGNORECASE
)

    # Replaces try_cast(convert(varchar, \"date_column\", 112) as int)
    calculation = re.sub(
    r"try_cast\s*\(\s*convert\s*\(\s*varchar\s*,\s*(\"[^\"].*?\")\s*,\s*112\s*\)\s*as\s*int\s*\)",
    lambda m: f"try_cast(to_varchar({m.group(1).replace(' ', '')}, 'YYYYMMDD') as int)",
    calculation,
    flags=re.IGNORECASE)

    calculation = re.sub(
    r"convert\s*\(\s*varchar\s*(?:,\s*(.+?))?\s*\)",
    lambda m: f"TO_VARCHAR({m.group(1).strip() if m.group(1) else ''})",
    calculation,
    flags=re.IGNORECASE
)
    # Replaces CAST/TRY_CAST(as CHAR) to CAST/TRY_CAST( as VARCHAR)
    calculation = re.sub(
    r"TRY_CAST\s*\(\s*\"?\s*([\w\s]+)\s*\"?\s*AS\s*CHAR\s*(?:\(\s*(\d+)\s*\))?\s*\)",
    lambda m: f'TRY_CAST("{m.group(1).strip()}" AS VARCHAR({m.group(2).strip()}))' if m.group(2) else f'TRY_CAST("{m.group(1).strip()}" AS VARCHAR)',
    calculation,
    flags=re.IGNORECASE)

    calculation = re.sub(
    r"CAST\s*\(\s*\"?\s*([\w\s]+)\s*\"?\s*AS\s*CHAR\s*(?:\(\s*(\d+)\s*\))?\s*\)",
    lambda m: f'CAST("{m.group(1).strip()}" AS VARCHAR({m.group(2).strip()}))' if m.group(2) else f'CAST("{m.group(1).strip()}" AS VARCHAR)',
    calculation,
    flags=re.IGNORECASE)

    # Replaces STR() with TO_VARCHAR()
    calculation = re.sub(
    r"\bSTR\s*\(\s*\"?\s*([\w]+)\s*\"?\s*\)",
    lambda m: f'TO_VARCHAR("{m.group(1).strip()}")' if '"' in m.group(0) else f'TO_VARCHAR({m.group(1).strip()})',
    calculation,
    flags=re.IGNORECASE)

    # Handling individual function transformations
    calculation = re.sub(r"GETDATE\(\)", "CURRENT_TIMESTAMP()", calculation, flags=re.IGNORECASE)

    # Replacing IIF with IFF for Snowflake
    calculation = re.sub(r"IIF\(([^,]+),\s*\"([^\"]+)\"\s*,\s*\"([^\"]+)\"\s*\)", r"IFF(\1, '\2', '\3')", calculation, flags=re.IGNORECASE)

    # Replaces cast( as datetime)
    calculation = re.sub(
    r"CAST\s*\(\s*([\"']?)\s*([\w\s:-]+)\s*\1\s*AS\s*DATETIME\s*\)",
    lambda m: f"CAST({m.group(1)}{m.group(2).strip()}{m.group(1)} AS TIMESTAMP_NTZ)",
    calculation,
    flags=re.IGNORECASE
)

    # Replaces STRING_AGG with LISTAGG
    calculation = re.sub(r'STRING_AGG\s*\(\s*("?\s*[\w]+?\s*"?)\s*,\s*\'\s*,\s*\'\s*\)', lambda m: f'LISTAGG({m.group(1).strip()}, \', \') WITHIN GROUP (ORDER BY {m.group(1).strip()})', calculation, flags=re.IGNORECASE)

    # Replacing ISNULL with COALESCE for Snowflake
    calculation = re.sub(r"ISNULL\s*\(\s*([\w\"\.]+)\s*,\s*([^)]+)\s*\)", r"COALESCE(\1, \2)", calculation, flags=re.IGNORECASE)

    double_quotes_pattern = r'(?i)(?<![=<>!])"([a-zA-Z_][a-zA-Z0-9_]*)"(?!\s*(=|<>|<|>|in|then))'
    calculation = re.sub(double_quotes_pattern, lambda match: f'"{match.group(1).upper()}"', calculation)
    # Handling CASE statement transformations separately
    if ("case" in calculation.lower() and "when" in calculation.lower()) or  "cast" in calculation.lower() or  "concat" in calculation.lower() or  "||" in calculation.lower() \
            or "coalesce" in calculation.lower() or ("select" in calculation.lower() and "from" in calculation.lower()):
        before_operators_pattern = r'(?i)(?<!\w)"([a-zA-Z_][a-zA-Z0-9_]*)"(?=\s*(=|<>|<|>|in))'
        calculation = re.sub(before_operators_pattern, lambda match: f'"{match.group(1).upper()}"', calculation)

        after_operators_pattern = r'([=<>]| in )(?!\s*(then|else))\s*"([^"]+)"'
        calculation = re.sub(after_operators_pattern, lambda match: f"{match.group(1)} '{match.group(2)}'", calculation)

        #double_quotes_pattern = r'(?i)(?<![=<>!])"([a-zA-Z_][a-zA-Z0-9_]*)"(?!\s*(=|<>|<|>|in|then))'
        #calculation = re.sub(double_quotes_pattern, lambda match: f'"{match.group(1).upper()}"', calculation)

    return calculation

# Streamlit UI
st.title("SQL Transformer")

input_sql = st.text_area("Input SQL:")
if st.button("Transform"):
    transformed_sql = transform_sql_expression(input_sql)
    st.text_area("Transformed SQL:", value=transformed_sql)