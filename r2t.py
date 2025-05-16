# Implement a demo from https://www.cse.ust.hk/~yike/R2T.pdf
import math
import time
from collections import defaultdict
from typing import List, Dict, Tuple, Any

import duckdb
import numpy as np
import pulp
from pulp import LpVariable

from create_tpch import query

# Type: Single primary private relation, from TPCH Q_{12}
# Primary private relation: orders
QUERY_12 = """select o_orderkey from orders, lineitem where o_orderkey = l_orderkey"""

# Type: Multiple primary private relations, from TPCH Q_{5}
# Primary private relations: supplier, customer
QUERY_5 = """SELECT
    s_suppkey,
    c_custkey
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

# Type: Aggregation
# Primary private relation: supplier, customer
QUERY_7 = """
SELECT
    s_suppkey,
    c_custkey,
    (l_extendedprice * (1 - l_discount))/10000 
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



# > "The one with scale 1 (default scale) has about 7.5 million tuples, and we set 𝐺𝑆𝑄= 10^6"
# I use scale 0.1, so set to 1e5
GSQ = 1 * pow(10, 5)
LOG_GSQ = math.log(GSQ, 2)
EPSILON = 0.8
BETA = 0.1


def get_join_result(query: str) -> List[Tuple]:
    duckdb.connect()
    con = duckdb.connect('tpch.duckdb')
    con.execute(query)
    result = con.fetchall()
    con.close()
    return result


def prepare_lp_solver(joined_row: List[Tuple]) -> (List[LpVariable], Dict[int, List[LpVariable]]):
    rows_num = len(joined_row)
    # variables is [u_0, u_1, ... u_k]
    variables = []
    for i in range(rows_num):
        # upBound is 0 \psi(q_k(I)), for a counter problem is 1
        variables.append(LpVariable(f'u_{i}', lowBound=0, upBound=1))
    m = defaultdict(list)
    for i, row in enumerate(joined_row):
        m[row[0]].append(variables[i])
    return variables, m

def prepare_lp_solver_multiple(joined_row: List[Tuple]) -> (List[LpVariable], Dict[Tuple[int, int], List[LpVariable]]):
    rows_num = len(joined_row)
    # variables is [u_0, u_1, ... u_k]
    variables = []
    for i in range(rows_num):
        # upBound is 0 \psi(q_k(I)), for a counter problem is 1
        variables.append(LpVariable(f'u_{i}', lowBound=0, upBound=1))
    m = defaultdict(list)
    for i, row in enumerate(joined_row):
        m[(row[0], row[1])].append(variables[i])
    return variables, m

def prepare_lp_solver_aggregation(joined_row: List[Tuple]) -> (List[LpVariable], Dict[Tuple[int, int], List[LpVariable]]):
    # variables is [u_0, u_1, ... u_k]
    variables = []
    for i, row in enumerate(joined_row):
        # upBound is 0 \psi(q_k(I)), for a counter problem is value(Tuple[1])
        variables.append(LpVariable(f'u_{i}', lowBound=0, upBound=row[2]))
    m = defaultdict(list)
    for i, row in enumerate(joined_row):
        m[(row[0],row[1])].append(variables[i])
    return variables, m

def solve_lp(variables: List[LpVariable], grouped_variables: Dict[Any, List[LpVariable]], tau: int) -> float:
    prob = pulp.LpProblem("Dummy", pulp.LpMaximize)
    prob += pulp.lpSum(variables)
    for value in grouped_variables.values():
        prob += pulp.lpSum(value) <= tau
    prob.solve()
    return pulp.value(prob.objective)


def calculate(variables: List[LpVariable], grouped_variables: Dict[Any, List[LpVariable]], tau: int) -> Tuple[
    float, float]:
    raw_result = solve_lp(variables, grouped_variables, tau)
    lap = np.random.laplace(loc=0, scale=LOG_GSQ * tau / EPSILON)
    lap = lap - LOG_GSQ * math.log(LOG_GSQ / BETA) * tau / EPSILON
    result = raw_result + lap
    return raw_result, result


def main():
    real_result = query(12)
    results = []
    for i in range(0,1):
        rows = get_join_result(QUERY_12)
        variables, grouped_variables = prepare_lp_solver(rows)
        # variables, grouped_variables = prepare_lp_solver_multiple(rows)
        # variables, grouped_variables = prepare_lp_solver_aggregation(rows)
        qi = [calculate(variables, grouped_variables, tau=0)]
        for j in range(1, int(LOG_GSQ) + 1):
            qi.append(calculate(variables, grouped_variables, tau=2 ** j))
        q_hat = -1
        for q in qi:
            if q[1] > q_hat:
                q_hat = q[1]
        result = {
            "i": i,
            "real_result": real_result,
            "q_hat": q_hat,
            "q_i": qi,
            "relative_error": f"{abs(q_hat - real_result) / real_result * 100}%",
        }
        results.append(result)
    # with open('result.jsonl', 'w') as f:
    #     for result in results:
    #         f.write(f"{result}\n")


if __name__ == '__main__':
    main()
