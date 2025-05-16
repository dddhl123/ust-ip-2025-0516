# Report


Project Link: https://github.com/dddhl123/ust-ip-2025-0516.git

## Background and Related Work

In recent years, **differential privacy** (DP) has emerged as the gold standard for protecting individual privacy in data analysis and release. DP has been adopted by major technology companies and government agencies, including Apple, Google, Microsoft, and the US Census Bureau, due to its strong theoretical guarantees that the inclusion or exclusion of any single individual's data does not significantly affect the outcome of any analysis. This property is typically achieved by adding carefully calibrated random noise to query results, with the amount of noise determined by the query's sensitivity—the maximum possible change in the output caused by modifying a single individual's data.

While the Laplace mechanism is a standard approach for achieving DP by adding noise proportional to the global sensitivity of a query, it faces significant challenges in the context of relational databases, especially when queries involve foreign-key (FK) constraints and self-joins. In many real-world databases, such as those used in customer relationship management or e-commerce, data about individuals is distributed across multiple tables linked by foreign keys. For example, a customer table may be linked to an orders table, where each customer can have an unbounded number of orders. In such cases, the global sensitivity of even simple join queries can be unbounded, rendering the Laplace mechanism ineffective due to the excessive noise required to preserve privacy.

To address this, prior work introduced the truncation mechanism, which limits the contribution of any individual by removing (truncating) those with excessive associated data before applying the Laplace mechanism. However, choosing the optimal truncation threshold (τ) is non-trivial, especially when queries involve self-joins, as the dependencies between individuals' data can lead to complex correlations and invalidate naive truncation approaches.

The R2T (Race-to-the-Top) mechanism, proposed by Dong et al. 2022, represents a significant advance in this area. R2T provides the differentially private mechanism capable of answering arbitrary SPJA (Selection, Projection, Join, Aggregation) queries in relational databases with foreign-key constraints. It achieves near-instance-optimal utility by adaptively selecting the truncation threshold in a differentially private manner, even in the presence of self-joins. R2T leverages a combination of truncation and linear programming (LP)-based techniques to ensure both privacy and utility, and is designed to be simple enough for practical deployment on top of standard relational database management systems (RDBMS) and LP solvers.

## Implementation

### Rewrite Query

For the simplest case of a single primary private relation, such as TPC-H Q12, if we choose "orders" as the primary private relation, I rewrote the SQL query to obtain the order key in order to extract the $Cj(I)$ required by the LP.

```sql
select count(*) from orders, lineitem where o_orderkey = l_orderkey
```

```sql
select o_orderkey from orders, lineitem where o_orderkey = l_orderkey
```

For multiple primary private relations, such as in query 5, if we choose both "supplier" and "customer" as the primary private relations, then according to Section 8 (MULTIPLE PRIMARY PRIVATE RELATIONS) of the paper, we first create an 𝑅𝑃(ID) generated from these two relations. For query 5, what I actually do is use the `tuple [supplier key, customer key]` as the grouping key for generating $C_j(I)$

```sql
SELECT
-    count(*)
+    s_suppkey,
+    c_custkey
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
```

For aggregation query, such as query 7. It is also a multiple primary private relations. I choose "supplier" and "customer" as primary private relations. I rewrite the query as follows:

```sql
SELECT
-		 sum((l_extendedprice * (1 - l_discount))/10000)
+    s_suppkey,
+    c_custkey,
+    (l_extendedprice * (1 - l_discount))/10000 
FROM
    supplier,
    lineitem,
    orders,
    customer
WHERE
    s_suppkey = l_suppkey
    AND o_orderkey = l_orderkey
    AND c_custkey = o_custkey
```

### Implementation Details

$$
\begin{align*}
\text{maximize} \quad & Q(I, \tau) = \sum_{k=1}^{N} u_k \\
\text{subject to} \quad & \sum_{k \in C_j(I)} u_k \leq \tau, \quad \forall j \in [M] \\
& 0 \leq u_k \leq \psi(q_k(I)), \quad \forall k \in [N]
\end{align*}
$$

The core of the R2T mechanism is to solve the above linear program (LP) for different values of $τ$ . In practice, this means for each candidate $τ$ , we maximize the sum of variables $u_k$ , where each $u_k$ represents the contribution of a join result $q_k(I)$ to the final query answer, subject to the constraint that the total contribution for each individual (or group, in the case of multiple primary private relations) does not exceed $τ$ . The upper bound $ψ(q_k(I))$ is typically 1 for counting queries, or the value of the aggregation for sum queries.

#### LP Solver Choice

The original paper uses CPLEX for LP solving, but due to licensing and size restrictions, I chose to use the community-supported [PuLP](https://github.com/coin-or/pulp/tree/master) library. PuLP is a Python-based modeling language for linear programming, which can interface with several open-source and commercial solvers.

#### Implementation Functions

- **prepare_lp_solver**:

  For the case of a single primary private relation (e.g., TPC-H Q12 with "orders" as the primary private relation), this function creates one LP variable for each join result, and groups them by the primary key (e.g., order key) to form the $C_j(I)$ sets.

- **prepare_lp_solver_multiple**:

  For queries with multiple primary private relations (e.g., both "supplier" and "customer" as primary private relations), this function uses the tuple of primary keys as the grouping key for $C_j(I)$

- **prepare_lp_solver_aggregation**:

  For aggregation queries (e.g., SUM), the upper bound for each LP variable $u_k$ is set to the value of the aggregation in that row, rather than 1.

- **solve_lp**:

  This function constructs the LP using PuLP, adds the objective and constraints, solves it, and returns the optimal value.

## Experiement

#### Codebase

Codebase is managed by `uv`. Please run `uv run .py` to reproduce.

- `create_tpch.py`: Use duckdb to create TPCH tables
- `r2t.py`: Main experiement file that implements the algorithm, this file will produce `result_{i}.jsonl` result file.
- `analyze.py`: Analyze `result_[5,7,12].jsonl` and create diagrams in this report

#### Environment:

- Hardware: `Mac M1` + `16 GB Memory`
- Software: `Python 3.12.7`

For each type, I ran **10 times** and took the average value of the Relative Error. The original experimental results can be found in the json files in the CodeBase. 

The result shows as follows:

| TPCH Query | Query Type                       | Avg Relative Error (%) | Query Result | Time (s) |
| ---------- | -------------------------------- | ---------------------- | ------------ | -------- |
| 12         | Single Primary Private + Count   | 0.150                  | 600572       | 30.94    |
| 5          | Multiple Primary Private + Count | 0.982                  | 23903        | 6.53     |
| 7          | Multiple Primary Private + Sum   | 0.088                  | 2053507      | 47.94    |

<img src="/Users/lqyue/Library/Application Support/typora-user-images/image-20250512115442095.png" alt="image-20250512115442095" style="zoom:77%;" />

## Conclusion

In conclusion, this project demonstrates the implementation of the R2T mechanism for differentially private query answering on relational databases with foreign-key constraints. By leveraging adaptive truncation and LP-based optimization, the approach achieves strong privacy guarantees with minimal utility loss, as evidenced by low relative errors across various TPC-H queries. 
