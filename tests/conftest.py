"""Shared fixtures: an in-memory S3 stand-in and ready-made Settings per role."""

from __future__ import annotations

import io
from typing import Any

import pytest
from botocore.exceptions import ClientError

from quant import data


class FakeS3:
    """Just enough of the boto3 S3 client for quant.data: head/put/get/list."""

    def __init__(self) -> None:
        self.store: dict[tuple[str, str], bytes] = {}
        self.puts: list[str] = []

    def head_object(self, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803 - boto3 names
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        return {"ContentLength": len(self.store[(Bucket, Key)])}

    def put_object(self, Bucket: str, Key: str, Body: bytes, **_: Any) -> dict[str, Any]:  # noqa: N803
        self.store[(Bucket, Key)] = bytes(Body)
        self.puts.append(Key)
        return {}

    def get_object(self, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        if (Bucket, Key) not in self.store:
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": "no"}}, "GetObject")
        return {"Body": io.BytesIO(self.store[(Bucket, Key)])}

    class _Paginator:
        def __init__(self, outer: FakeS3) -> None:
            self.outer = outer

        def paginate(self, Bucket: str, Prefix: str = "") -> Any:  # noqa: N803
            contents = [
                {"Key": k, "Size": len(v), "LastModified": None}
                for (b, k), v in sorted(self.outer.store.items())
                if b == Bucket and k.startswith(Prefix)
            ]
            yield {"Contents": contents}

    def get_paginator(self, name: str) -> Any:
        assert name == "list_objects_v2"
        return FakeS3._Paginator(self)


def _cfg(role: str, handle: str = "tester") -> data.Settings:
    return data.Settings(
        account_id="acc",
        endpoint="https://acc.eu.r2.cloudflarestorage.com",
        bucket="test-bucket",
        access_key_id="k",
        secret_access_key="s",
        handle=handle,
        role=role,
    )


@pytest.fixture
def s3() -> FakeS3:
    return FakeS3()


@pytest.fixture
def user_cfg() -> data.Settings:
    return _cfg("user")


@pytest.fixture
def ingest_cfg() -> data.Settings:
    return _cfg("ingest")


@pytest.fixture
def promote_cfg() -> data.Settings:
    return _cfg("promote")
