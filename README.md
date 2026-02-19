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

When using IAM Roles for Service Accounts (IRSA), pass `aws_access_key_id` and `aws_secret_access_key` as empty strings so that the AWS SDK uses its default credential provider chain (which will pick up the service account role). You should still provide a valid `aws_region` here, or ensure that `AWS_REGION` or `AWS_DEFAULT_REGION` is set in the environment or shared AWS config when omitting it.

[Steps to Publish Package](https://github.com/Orange-Health/pubsublib-python/wiki/PyPI-%7C-Publish-Package#steps-to-publish-the-pubsublib-package-on-pypi)

