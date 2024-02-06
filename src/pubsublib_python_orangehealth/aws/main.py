import boto3
from botocore.exceptions import ClientError
import logging
import boto3.session
from src.pubsublib_python_orangehealth.aws.sns_wrapper import SnsWrapper
from src.pubsublib_python_orangehealth.aws.utils.helper import bind_attributes, is_large_message, validate_message_attributes
from src.pubsublib_python_orangehealth.infrastructure.cache_adapter import CacheAdapter
import uuid

logger = logging.getLogger(__name__)


class AWSPubSubAdapter():
    def __init__(
        self,
        aws_region,
        aws_access_key_id,
        aws_secret_access_key,
        sns_endpoint,
        redis_location
    ):
        self.my_session = boto3.session.Session(
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        self.sns_client = self.my_session.client("sns", endpoint_url=sns_endpoint)
        self.sqs_client = self.my_session.client("sqs")
        self.cache_adapter = CacheAdapter(redis_location)

    def create_topic(
        self,
        topic_name
    ):
        """
        Creates a notification topic.

        :param topic_name: The topic_name of the topic to create.
        :return: The newly created topic.
        """
        try:
            topic = self.sns_client.create_topic(Name=topic_name)
            logger.info("Created topic %s with ARN %s.", topic_name, topic.arn)
        except ClientError:
            logger.exception("Couldn't create topic %s.", topic_name)
            raise
        else:
            return topic

    def create_topic_fifo(
        self,
        topic_name
    ):
        """
        Create a FIFO topic.
        Topic names must be made up of only uppercase and lowercase ASCII letters,
        numbers, underscores, and hyphens, and must be between 1 and 256 characters long.
        For a FIFO topic, the name must end with the .fifo suffix.

        :param topic_name: The name for the topic.
        :return: The new topic.
        """
        try:
            if topic_name.endswith(".fifo"):
                topic = self.sns_client.create_topic(
                    Name=topic_name,
                    Attributes={
                        "FifoTopic": str(True),
                        "ContentBasedDeduplication": str(False),
                    },
                )
                logger.info("Created FIFO topic with name=%s.", topic_name)
                return topic
            else:
                logger.error("FIFO Topic name must end with .fifo!")
                return None
        except ClientError as error:
            logger.exception("Couldn't create topic with name=%s!", topic_name)
            raise error

    def publish_message(
        self,
        topic_arn,
        message,
        attributes
    ):
        """
        Publishes a message, with attributes, to a topic. Subscriptions can be filtered
        based on message attributes so that a subscription receives messages only
        when specified attributes are present.

        :param topic: The topic to publish to.
        :param message: The message to publish.
        :param attributes: The key-value attributes to attach to the message. Values
                           must be either `str` or `bytes`.
        :return: The ID of the message.
        """
        try:
            if is_large_message(message):
                # body is larger than 200kB. Best to put it in redis with expiry time of 10 days
                redis_key = uuid.uuid4()
                attributes["redis_key"] = redis_key
                self.cache_adapter.set(redis_key, message, 10*24*60)

            if validate_message_attributes(message_attributes):
                message_attributes = bind_attributes(attributes)
                response = self.sns_client.publish(
                    TopicArn=topic_arn,
                    Message=message,
                    MessageAttributes=message_attributes
                )
                message_id = response["MessageId"]
        except ClientError:
            logger.exception(
                "Couldn't publish message to topic %s.", topic_arn)
            return None
        else:
            return message_id

    def publish_message_fifo(
        self,
        topic_arn,
        message,
        message_group_id,
        message_deduplication_id,
        attributes
    ):
        """
        Publishes a message to a FIFO topic. The message_group_id and message_deduplication_id
        are used to ensure that the message is processed in the correct order and that
        duplicate messages are not sent.

        :param topic: The topic to publish to.
        :param message: The message to publish.
        :param message_group_id: The message group ID.
        :param message_deduplication_id: The message deduplication ID.
        :param attributes: The key-value attributes to attach to the message. Values
                           must be either `str` or `bytes`.
        :return: The ID of the message.
        """
        try:
            if is_large_message(message):
                # body is larger than 200kB. Best to put it in redis with expiry time of 10 days
                redis_key = uuid.uuid4()
                attributes["redis_key"] = redis_key
                self.cache_adapter.set(redis_key, message, 10*24*60)

            if validate_message_attributes(message_attributes):
                message_attributes = bind_attributes(attributes)
                response = self.sns_client.publish(
                    TopicArn=topic_arn,
                    Message=message,
                    MessageGroupId=message_group_id,
                    MessageDeduplicationId=message_deduplication_id,
                    MessageAttributes=message_attributes
                )
                message_id = response["MessageId"]
        except ClientError:
            logger.exception(
                "Couldn't publish message to FIFO topic %s.", topic_arn)
        else:
            return message_id

    def create_queue(self, name):
        """
        Creates a queue.

        :param name: The name of the queue to create.
        :param deadletter_queue_name: The name of the deadletter queue to associate with the queue.
        :return: The newly created queue.
        """
        try:
            queue = self.sqs_client.create_queue(QueueName=name)
            logger.info("Created queue %s with URL %s.", name, queue.url)
        except ClientError:
            logger.exception("Couldn't create queue %s.", name)
            raise
        else:
            return queue

    def create_queue_fifo(self, name):
        """
        Creates a FIFO queue.

        :param name: The name of the queue to create.
        :return: The newly created queue.
        """
        try:
            if name.endswith(".fifo"):
                queue = self.sqs_client.create_queue(
                    QueueName=name,
                    Attributes={
                        "FifoQueue": "true"
                    },
                )
                logger.info("Created FIFO queue with name=%s.", name)
                return queue
            else:
                logger.error("FIFO Queue name must end with .fifo!")
                return None
        except ClientError as error:
            logger.exception("Couldn't create FIFO queue with name=%s!", name)
            raise error

    def poll_message_from_queue(
        self,
        sqs_queue_url: str,
        handler,
        visibility_timeout: int = 20,
        wait_time_seconds: int = 0,
        message_attribute_names: list = ['All'],
        max_number_of_messages: int = 10,
        attribute_names: list = ['All']
    ):
        """
            The Message response will look something like:
            {
                'MessageId': 'c6af9ac6-7b61-11e6-9a41-93e8deadbeef',
                'ReceiptHandle': 'MessageReceiptHandle',
                'MD5OfBody': '275a635e474a51e0c5a2d638b19ba19e',
                'Body': 'Hello from SQS!',
                'Attributes': {
                    'SentTimestamp': '1477981389573'
                },
                'MessageAttributes': {},
                'MD5OfMessageAttributes': '275a635e474a51e0c5a2d638b19ba19e'
            }
        """

        recieved_message = self.sqs_client.receive_message(
            QueueUrl=sqs_queue_url,
            MaxNumberOfMessages=max_number_of_messages,
            VisibilityTimeout=visibility_timeout,
            WaitTimeSeconds=wait_time_seconds,
            MessageAttributeNames=message_attribute_names,
            AttributeNames=attribute_names
        )

        if 'Messages' in recieved_message:
            for message in recieved_message['Messages']:
                processing_result = handler(message)
                if processing_result:
                    self.sqs_client.delete_message(
                        QueueUrl=sqs_queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
        else:
            print("No messages received.")

        return message

    def subscribe_to_topic(
        self,
        sns_topic_arn: str,
        sqs_queue_arn: str
    ):
        """
            The SubscriptionArn response will look something like:
            {
                "SubscriptionArn": "arn:aws:sns:us-west-2:123456789012:MyTopic:5be8f5b7-6a41-41c9-98e2-9c8e8f946b7d"
            }
        """

        subscription = self.sns_client.subscribe(
            TopicArn=sns_topic_arn,
            Protocol="sqs",
            Endpoint=sqs_queue_arn,
            ReturnSubscriptionArn=True
        )

        return subscription

"""
a = AWSPubSubAdapter()
result = a.publish_message_to_pubsub(
    message="Hello from pubsublib! 54564",
    sns_topic_arn="arn:aws:sns:ap-south-1:606514307308:pubsublib-django-testing",
    region="ap-south-1"
)

# result = a.poll_message_from_queue(
#     sqs_queue_url="https://sqs.ap-south-1.amazonaws.com/606514307308/pubsublib-django-testing",
#     region="ap-south-1"
# )

print(result)
"""
