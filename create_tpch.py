import duckdb

QUERY_12 = """select count(*) from orders, lineitem where o_orderkey = l_orderkey"""


QUERY_5 = """SELECT
    count(*)
FROM
    customer,
    orders,
    lineitem,
    supplier,
    nation,
    region
WHERE
    c_custkey = o_custkey
    AND l_orderkey = o_orderkey
    AND l_suppkey = s_suppkey
    AND c_nationkey = s_nationkey
    AND s_nationkey = n_nationkey
    AND n_regionkey = r_regionkey
"""


QUERY_7 = """
    SELECT
        sum((l_extendedprice * (1 - l_discount))/10000)
    FROM
        supplier,
        lineitem,
        orders,
        customer
    WHERE
        s_suppkey = l_suppkey
        AND o_orderkey = l_orderkey
        AND c_custkey = o_custkey
"""

def create_tpch(scale_factor = 0.1):
    con = duckdb.connect('tpch.duckdb')
    con.install_extension("tpch")
    con.load_extension("tpch")
    con.execute(f"CALL dbgen(sf = {scale_factor})")
    con.close()

def show_schema():
    con = duckdb.connect('tpch.duckdb')
    con.execute("DESCRIBE orders")
    print(con.fetchall())
    con.execute("DESCRIBE customer")
    print(con.fetchall())
    con.execute("DESCRIBE lineitem")
    print(con.fetchall())
    con.execute("DESCRIBE nation")
    print(con.fetchall())
    con.execute("DESCRIBE supplier")
    print(con.fetchall())
    con.execute("FROM tpch_queries()")
    print(con.fetchall())
    con.execute("PRAGMA tpch(5)")
    print(con.fetchall())
    con.close()

def show_count():
    con = duckdb.connect('tpch.duckdb')
    con.execute("SELECT COUNT(*) FROM orders")
    print("orders count:", con.fetchone()[0])
    con.execute("SELECT COUNT(*) FROM customer")
    print("customer count:", con.fetchone()[0])
    con.execute("SELECT COUNT(*) FROM lineitem")
    print("lineitem count:", con.fetchone()[0])
    con.close()

def query(query_num:int):
    query = ""
    if query_num == 12:
        query = QUERY_12
    elif query_num == 5:
        query = QUERY_5
    elif query_num == 7:
        query = QUERY_7
    else:
        raise ValueError("Invalid query number. Choose 12, 5, or 7.")
    con = duckdb.connect('tpch.duckdb')
    con.execute(query)
    result = con.fetchall()
    return result[0][0]

if __name__ == '__main__':
    # create_tpch()
    show_schema()
    show_count()