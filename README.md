# pubsublib

pubsublib is a Python library designed for PubSub functionality using AWS - SNS & SQS.

## PIP Package
[pubsublib](https://pypi.org/project/pubsublib/)

## Getting Started
To get started with pubsublib, you can install it via pip:

```bash
pip install pubsublib
```

## Using Pubsublib
Once pubsublib is installed, you can use it in your Python code as follows:

```python
from pubsublib.aws.main import AWSPubSubAdapter

pubsub_adapter = AWSPubSubAdapter(
    aws_region='XXXXX',
    aws_access_key_id='XXXXX',
    aws_secret_access_key='XXXXX',
    redis_location='XXXXX',
    sns_endpoint_url=None,
    sqs_endpoint_url=None
)
```

#### Using AWS IAM Roles for Service Accounts 

When using IAM Roles for Service Accounts (IRSA), pass `aws_access_key_id` and `aws_secret_access_key` as empty strings so that the AWS SDK uses its default credential provider chain (which will pick up the service account role). Always pass a valid `aws_region` — it is applied to the boto3 session even when credentials are empty (required to avoid `NoRegionError` when `AWS_DEFAULT_REGION` is unset).

#### SQS server-side encryption (SSE-SQS)

Optional adapter setting — **off by default**, fully backward compatible. Existing `AWSPubSubAdapter(...)` calls work unchanged.

```python
pubsub_adapter = AWSPubSubAdapter(
    aws_region='ap-south-1',
    aws_access_key_id='',
    aws_secret_access_key='',
    redis_location='redis://localhost:6379/0',
    sqs_managed_sse_enabled=True,  # optional; omit or pass False to keep current behaviour
)
```

All `create_queue` calls on that adapter then set `SqsManagedSseEnabled=true`. If the queue already exists, SSE is applied via `SetQueueAttributes`. You can also toggle at runtime with `set_sqs_managed_sse_enabled(True)`.

[Steps to Publish Package](https://github.com/Orange-Health/pubsublib-python/wiki/PyPI-%7C-Publish-Package#steps-to-publish-the-pubsublib-package-on-pypi)

