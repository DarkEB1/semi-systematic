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

-- raw: daily FRED series in long format (series listed in catalog/reference/fred_series.csv)
CREATE OR REPLACE VIEW fred_series_daily AS
SELECT * FROM read_parquet('s3://{bucket}/raw/fred/series_daily/*/*/*.parquet', hive_partitioning = true, union_by_name = true);

CREATE OR REPLACE VIEW ref_fred_series AS
SELECT * FROM read_csv_auto('{repo}/catalog/reference/fred_series.csv', header = true);

-- raw: eur_series_daily from ecb (daily)
CREATE OR REPLACE VIEW ecb_eur_series_daily AS
SELECT * FROM read_parquet('s3://{bucket}/raw/ecb/eur_series_daily/*/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- raw: brl_series_daily from bcb (daily)
CREATE OR REPLACE VIEW bcb_brl_series_daily AS
SELECT * FROM read_parquet('s3://{bucket}/raw/bcb/brl_series_daily/*/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- raw: vol_indices_daily from cboe (daily)
CREATE OR REPLACE VIEW cboe_vol_indices_daily AS
SELECT * FROM read_parquet('s3://{bucket}/raw/cboe/vol_indices_daily/*/*/*.parquet', hive_partitioning = true, union_by_name = true);

-- raw: tff_fx_weekly from cftc (daily)
CREATE OR REPLACE VIEW cftc_tff_fx_weekly AS
SELECT * FROM read_parquet('s3://{bucket}/raw/cftc/tff_fx_weekly/*/*/*.parquet', hive_partitioning = true, union_by_name = true);
