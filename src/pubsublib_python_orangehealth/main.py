from abc import ABC, abstractmethod

class PubSubAdapter(ABC):
    """
    The MessageId response will look something like:
    {
    "MessageId": "7c446cbb-fb6a-4c03-bc0b-ded3641d5579",
    "ResponseMetadata": {
        "RequestId": "f187a3c1-376f-11df-8963-01868b7c937a",
        "HTTPStatusCode": 200,
        "HTTPHeaders": {
        "server": "amazon.com"
        },
        "RetryAttempts": 0
    }
    }
    """
    def publish_message_to_sns(message: str):
        topic_arn = os.environ["sns_topic_arn"]

        sns_client = boto3.client(
            "sns",
            region_name="eu-west-1",
        )

        message_id = sns_client.publish(
            TopicArn=topic_arn,
            Message=message,
        )

        return message_id

    def add_one(number):
        return number + 1
