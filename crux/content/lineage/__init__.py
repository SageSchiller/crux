"""lineage scenarios: synthetic domains, and the cheapest way through them.

Each module authors the **structure** of a domain: which principals exist and
which rights connect them. Names, ordering and padding are drawn per seed by
`crux/targets/_graph.py` (crux D10), so the answer is a set of rights rather
than a set of names, and a scenario cannot be beaten by remembering which row
the path was on.

Every scenario names what it teaches, and `validate.py` proves the graph
actually has that property rather than trusting the label.
"""
