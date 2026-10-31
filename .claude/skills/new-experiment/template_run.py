import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    import pathlib

    import marimo as mo
    import yaml

    from quant import data

    HERE = pathlib.Path(__file__).resolve().parent
    config = yaml.safe_load((HERE / "config.yaml").read_text(encoding="utf-8"))
    mo.md(f"# {config['slug']}\n\n{config.get('hypothesis', '')}")
    return HERE, config, data, json, mo


@app.cell
def _(config, data):
    # Only the datasets named in config.yaml, at the snapshots named there.
    tables = data.load(config)
    tables
    return (tables,)


@app.cell
def _(HERE, config, json, tables):
    # Everything --finish may quote must be written to outputs/. No other numbers count.
    out = HERE / "outputs"
    out.mkdir(exist_ok=True)
    metrics = {
        "seed": config.get("seed"),
        "datasets_loaded": len(tables),
        "rows": {k: v.num_rows for k, v in tables.items()},
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    metrics
    return


if __name__ == "__main__":
    app.run()
