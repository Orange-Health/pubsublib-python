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
)
```
