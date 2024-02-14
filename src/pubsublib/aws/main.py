import json
import boto3
from botocore.exceptions import ClientError
import logging
import boto3.session
from pubsublib.aws.utils.helper import bind_attributes, is_large_message, validate_message_attributes, is_message_integrity_verified
from pubsublib.common.cache_adapter import CacheAdapter
import uuid

logger = logging.getLogger(__name__)


class AWSPubSubAdapter():
    def __init__(
        self,
        aws_region: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        redis_location: str,
        sns_endpoint_url: str = None,
        sqs_endpoint_url: str = None
    ):
        self.my_session = boto3.session.Session(
            region_name=aws_region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        if sns_endpoint_url != None:
            self.sns_client = self.my_session.client("sns", endpoint_url=sns_endpoint_url)
        else:
            self.sns_client = self.my_session.client("sns")
        if sqs_endpoint_url != None:
            self.sqs_client = self.my_session.client("sqs", endpoint_url=sqs_endpoint_url)
        else:
            self.sqs_client = self.my_session.client("sqs")
        self.cache_adapter = CacheAdapter(redis_location)

    def create_topic(
        self,
        topic_name: str,
        is_fifo: bool
    ):
        """
        Creates a topic.

        :param topic_name: The name of the topic to create.
        :return: The newly created topic.
        """
        if is_fifo:
            return self.__create_topic_fifo(topic_name)
        else:
            return self.__create_topic_standard(topic_name)

    def __create_topic_standard(
        self,
        topic_name: str,
        tags: list = []
    ):
        """
        Creates a notification topic.

        :param topic_name: The topic_name of the topic to create.
        :return: The newly created topic.
        """
        try:
            topic = self.sns_client.create_topic(
                Name=topic_name,
                Tags=tags
            )
            logger.info("Created Standard topic %s with ARN %s.", topic_name, topic.arn)
        except ClientError:
            logger.exception("Couldn't create Standard topic %s.", topic_name)
            raise
        else:
            return topic

    def __create_topic_fifo(
        self,
        topic_name: str,
        tags: list = [],
        content_based_deduplication: bool = False
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
                        "FifoTopic": True,
                        "ContentBasedDeduplication": content_based_deduplication
                    },
                    Tags=tags
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
        topic_arn: str,
        message: str,
        attributes: dict,
        is_fifo: bool,
        message_group_id: str = None,
        message_deduplication_id: str = None
    ):
        """
        Publishes a message to a topic.

        :param topic: The topic to publish to.
        :param message: The message to publish.
        :param message_group_id: The message group ID.
        :param message_deduplication_id: The message deduplication ID.
        :param attributes: The key-value attributes to attach to the message. Values
                           must be either `str` or `bytes`.
        :return: The ID of the message.
        """
        if is_fifo:
            return self.__publish_message_fifo_queue(
                topic_arn,
                message,
                message_group_id,
                message_deduplication_id,
                attributes
            )
        else:
            return self.__publish_message_standard_queue(
                topic_arn,
                message,
                attributes
            )

    def __publish_message_standard_queue(
        self,
        topic_arn: str,
        message: str,
        attributes: dict
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

            if validate_message_attributes(attributes):
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

    def __publish_message_fifo_queue(
        self,
        topic_arn: str,
        message: str,
        message_group_id: str,
        message_deduplication_id: str,
        attributes: dict
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

            if validate_message_attributes(attributes):
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

    def create_queue(
        self,
        name: str,
        is_fifo: bool
    ):
        """
        Creates a queue.

        :param name: The name of the queue to create.
        :return: The newly created queue.
        """
        if is_fifo:
            return self.__create_fifo_queue(name)
        else:
            return self.__create_standard_queue(name)

    def __create_standard_queue(
            self, 
            name: str,
            visiblity_timeout: int = 30,
            message_retention_period: int = 345600,
            tags: list = []
        ):
        """
        Creates a queue.

        :param name: The name of the queue to create.
        :param deadletter_queue_name: The name of the deadletter queue to associate with the queue.
        :return: The newly created queue.
        """
        try:
            queue = self.sqs_client.create_queue(
                QueueName=name,
                Attributes={
                    "VisibilityTimeout": visiblity_timeout,
                    "MessageRetentionPeriod": message_retention_period
                },
                Tags=tags
            )
            logger.info("Created queue %s with URL %s.", name, queue.url)
        except ClientError:
            logger.exception("Couldn't create queue %s.", name)
            raise
        else:
            return queue

    def __create_fifo_queue(
            self, 
            name: str,
            visiblity_timeout: int = 30,
            message_retention_period: int = 345600, #4days
            content_based_deduplication: bool = True,
            tags: list = []
        ):
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
                        "FifoQueue": "true",
                        "VisibilityTimeout": visiblity_timeout,
                        "MessageRetentionPeriod": message_retention_period,
                        "ContentBasedDeduplication": content_based_deduplication
                    },
                    Tags=tags
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
        visibility_timeout: int = 15,
        wait_time_seconds: int = 20,
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
        try:
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
                    if not is_message_integrity_verified(message['Body'], message['MD5OfBody']):
                        raise ValueError(
                            "message corrupted, Message integrity verification failed!")
                    if message['MessageAttributes'] and 'redis_key' in message['MessageAttributes']:
                        redis_key = message['MessageAttributes']['redis_key']['Value']
                        message_body = self.fetch_value_from_redis(redis_key)
                        if message_body:
                            message['Body'] = message_body
                        else:
                            logger.exception("Couldn't find message body in redis with key=%s!", redis_key)
                            continue
                    processing_result = handler(message)
                    if processing_result:
                        self.sqs_client.delete_message(
                            QueueUrl=sqs_queue_url,
                            ReceiptHandle=message['ReceiptHandle']
                        )
            else:
                logger.info("No messages in queue with URL=%s!", sqs_queue_url)
            return recieved_message
        except ClientError as error:
            logger.exception(
                "Couldn't poll message from queue with URL=%s!", sqs_queue_url)
            raise error

    def subscribe_to_topic(
        self,
        sns_topic_arn: str,
        sqs_queue_arn: str,
        raw_message_delivery: bool = False,
        filter_policy: dict = None
    ):
        """
            The SubscriptionArn response will look something like:
            {
                "SubscriptionArn": "arn:aws:sns:us-west-2:123456789012:MyTopic:5be8f5b7-6a41-41c9-98e2-9c8e8f946b7d"
            }
        """
        self.__update_sns_iam_policy_to_push_message_to_sqs(
            sns_topic_arn,
            sqs_queue_arn
        )

        subscription = self.sns_client.subscribe(
            TopicArn=sns_topic_arn,
            Protocol="sqs",
            Endpoint=sqs_queue_arn,
            ReturnSubscriptionArn=True,
            Attributes={
                "RawMessageDelivery": raw_message_delivery,
                "FilterPolicy": json.dump(filter_policy) if filter_policy else None
            }
        )

        return subscription

    def fetch_value_from_redis(self, redis_key):
        """
        Fetches value from redis with the given key.
        """
        return self.cache_adapter.get(redis_key)

    def tag_resource(
        self,
        resource_arn: str,
        tags: dict
    ):
        """
        Adds tags to the specified Amazon SNS topic.

        :param resource_arn: The Amazon Resource Name (ARN) of the topic to tag.
        :param tags: The key-value tags to add to the topic.
        """
        try:
            self.sns_client.tag_resource(
                ResourceArn=resource_arn,
                Tags=tags
            )
        except ClientError:
            logger.exception(
                "Couldn't tag resource with ARN %s.", resource_arn)
            raise

    def __update_sns_iam_policy_to_push_message_to_sqs(
        self,
        sns_topic_arn: str,
        sqs_queue_arn: str
    ):
        """
        Updates the policy of the SNS topic to allow it to push messages to the SQS queue.

        :param sns_topic_arn: The ARN of the SNS topic.
        :param sqs_queue_arn: The ARN of the SQS queue.
        """
        try:
            policy = {
                "Version": "2012-10-17",
                "Id": f"{sns_topic_arn}-policy",
                "Statement": [
                    {
                        "Sid": f"{sns_topic_arn}-statement",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "sns.amazonaws.com"
                        },
                        "Action": "SQS:SendMessage",
                        "Resource": sqs_queue_arn,
                        "Condition": {
                            "ArnEquals": {
                                "aws:SourceArn": sns_topic_arn
                            }
                        }
                    }
                ]
            }
            policy = json.dumps(policy)
            self.sqs_client.set_queue_attributes(
                QueueUrl=sqs_queue_arn,
                Attributes={
                    "Policy": policy
                }
            )
        except ClientError:
            logger.exception(
                "Couldn't update SNS policy to push messages to SQS queue %s.", sqs_queue_arn)
            raise
