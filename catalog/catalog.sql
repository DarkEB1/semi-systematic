-- Catalog views. quant.data.connect() replaces {bucket} and {repo} and runs each statement;
-- a view whose files do not exist yet is skipped with a notice (strict=True to fail instead).
-- Naming: raw views are <source>_<dataset>; curated views are plain <dataset>; reference CSVs are ref_<name>.

-- raw: daily FX OHLCV from Yahoo (year=/month= partitions)
CREATE OR REPLACE VIEW yahoo_prices_daily AS
SELECT * FROM read_parquet('s3://{bucket}/raw/yahoo/prices_daily/*/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- curated: promoted snapshots (snapshot= partitions, schema contract in catalog/datasets/prices_daily.md)
CREATE OR REPLACE VIEW prices_daily AS
SELECT * FROM read_parquet('s3://{bucket}/curated/prices_daily/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- curated: the repo retrieval index uploaded by index.yml (snapshot=<git sha>)
CREATE OR REPLACE VIEW repo_index AS
SELECT * FROM read_parquet('s3://{bucket}/curated/repo_index/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- reference: small hand-maintained tables kept in git (1 MB cap)
CREATE OR REPLACE VIEW ref_universe AS
SELECT * FROM read_csv_auto('{repo}/catalog/reference/universe.csv', header = true);

-- raw: usd_reference_rates from nyfed (daily)
CREATE OR REPLACE VIEW nyfed_usd_reference_rates AS
SELECT * FROM read_parquet('s3://{bucket}/raw/nyfed/usd_reference_rates/*/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- raw: aave_reserve_daily from aave_archive (daily)
CREATE OR REPLACE VIEW aave_archive_aave_reserve_daily AS
SELECT * FROM read_parquet('s3://{bucket}/raw/aave_archive/aave_reserve_daily/*/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- curated: owner-reviewed research acquisition snapshots
CREATE OR REPLACE VIEW aave_reserve_daily AS
SELECT * FROM read_parquet('s3://{bucket}/curated/aave_reserve_daily/*/*.parquet', hive_partitioning = true, union_by_name = true);

CREATE OR REPLACE VIEW usd_reference_rates AS
SELECT * FROM read_parquet('s3://{bucket}/curated/usd_reference_rates/*/*.parquet', hive_partitioning = true, union_by_name = true);
