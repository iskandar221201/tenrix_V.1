import re

def _split_sql_statements(sql: str) -> list[str]:
    statements  = []
    current     = []
    in_string   = False
    string_char = None
    escaped     = False

    for char in sql:
        if in_string:
            current.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == string_char:
                in_string = False
        else:
            if char in ("'", '"'):
                in_string   = True
                string_char = char
                current.append(char)
                escaped     = False
            elif char == ";":
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(char)
    stmt = "".join(current).strip()
    if stmt:
        statements.append(stmt)
    return statements

sql = """
CREATE TABLE `t1` ( `id` int );
INSERT INTO `t1` VALUES ('it\'s a test');
"""

# Simulate the cleaning process partially
sql = sql.replace('`', '"')

stmts = _split_sql_statements(sql)
print(f"Count: {len(stmts)}")
for i, s in enumerate(stmts):
    print(f"{i}: {s}")
