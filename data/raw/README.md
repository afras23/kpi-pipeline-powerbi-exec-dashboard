# Raw data directory

This folder is where the ETL expects `customers.csv`, `products.csv`, and `order_lines.csv` (see the main README for column contracts).

**Nothing in this repository is real operational data.** For local development and demos, generate **synthetic** fixtures:

```bash
pip install -r requirements.txt
python etl/generate_synthetic_data.py
```

Output is deterministic (`numpy` seed 42). In production you would populate this directory from approved source-system exports or a secure ingestion path — and keep those files out of git.

`*.csv` files here are ignored by version control.
