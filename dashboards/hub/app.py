import marimo

__generated_with = "0.25.2"
app = marimo.App(width="full", app_title="semi-systematic hub")


@app.cell
def _():
    import pathlib
    import sys

    import marimo as mo

    HERE = pathlib.Path(__file__).resolve().parent
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from pages import agent_log, data_health, experiments, knowledge, signals

    PAGES = {
        "experiments": experiments,
        "data-health": data_health,
        "knowledge": knowledge,
        "agent-log": agent_log,
        "signals": signals,
    }
    page = mo.ui.dropdown(options=list(PAGES), value="experiments", label="page")
    return PAGES, mo, page


@app.cell
def _(mo):
    # Filters are globals so they stay reactive; each page reads the ones it needs.
    owner = mo.ui.text(label="owner")
    tag = mo.ui.text(label="tag")
    dataset = mo.ui.text(label="dataset")
    status = mo.ui.dropdown(
        options=["", "draft", "final", "active", "superseded"], value="", label="status"
    )
    query = mo.ui.text(label="search", placeholder="ILIKE over the chunk table")
    return dataset, owner, query, status, tag


@app.cell
def _(PAGES, dataset, mo, owner, page, query, status, tag):
    filters = {
        "owner": owner.value,
        "tag": tag.value,
        "dataset": dataset.value,
        "status": status.value,
        "query": query.value,
    }
    controls = {
        "experiments": [owner, tag, dataset, status],
        "knowledge": [query],
    }.get(page.value, [])
    body = PAGES[page.value].render(mo, filters)
    mo.vstack([mo.md("# semi-systematic hub"), mo.hstack([page, *controls]), body])
    return


if __name__ == "__main__":
    app.run()
