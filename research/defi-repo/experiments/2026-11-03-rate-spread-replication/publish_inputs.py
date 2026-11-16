"""Publish only validated, bounded acquisition tables to immutable scratch keys."""

import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq
import yaml

from quant import data

HERE = Path(__file__).resolve().parent


def main():
    out = HERE / "outputs"
    manifest = json.loads((out / "acquisition-manifest.json").read_text())
    assert len(manifest["checks"]) == 6 and manifest["total_bytes"] < 10_000_000
    config = yaml.safe_load((HERE / "config.yaml").read_text())
    cfg, client = data.settings(write=True), data.s3_client(write=True)
    assert cfg.role == "user" and cfg.handle == config["owner"]
    pins = []
    for item in manifest["datasets"]:
        name = item["name"]
        path = out / f"{name}.parquet"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["local_sha256"]
        table = pq.read_table(path)
        data.validate_schema(table, name)
        key = f"scratch/{cfg.handle}/defi-repo/{name}/snapshot={config['date']}/data.parquet"
        try:
            data.write_once(table, key, client=client, cfg=cfg)
        except data.ExistsError:
            pass  # A resumed publish must verify identical bytes; never overwrite.
        body = client.get_object(Bucket=cfg.bucket, Key=key)["Body"].read()
        digest = hashlib.sha256(body).hexdigest()
        assert digest == item["local_sha256"], "existing object differs from validated acquisition"
        pins.append(dict(name=name, snapshot=config["date"], scratch_key=key, sha256=digest))
        contract = data.DATASET_DOCS / f"{name}.md"
        for filename, text in [
            ("README.md", contract.read_text()),
            ("provenance.json", json.dumps(manifest, indent=2)),
        ]:
            text_key = key.removesuffix("data.parquet") + filename
            try:
                data.put_text(text, text_key, client=client, cfg=cfg)
            except data.ExistsError:
                existing = client.get_object(Bucket=cfg.bucket, Key=text_key)["Body"].read()
                assert existing == text.encode()
    config["datasets"] = pins
    (HERE / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    loaded = data.load(config)
    (HERE / "acquisition-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            {
                "published_and_read_back": {k: v.num_rows for k, v in loaded.items()},
                "parquet_bytes": manifest["total_bytes"],
                "pins": pins,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
