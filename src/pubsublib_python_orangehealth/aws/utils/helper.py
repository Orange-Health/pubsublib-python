import hashlib
import uuid


def is_large_message(message: str):
    """
    returns True if the message is larger than 200KB
    """
    return len(message) > 200 * 1024

def is_message_integrity_verified(message: str, md5_hash: str):
    """
    Check if the message integrity is verified, by comapring the MD5 hash of the message with the MD5 hash in the message attributes
    """
    return md5_hash == calculate_md5_hash(message)
    
def calculate_md5_hash(message: str):
    """
    Calculate the MD5 hash of the message
    """
    return hashlib.md5(message.encode()).hexdigest()

def get_queue_deadletter(self):
    if self._deadletter_queue_name:
        return self._deadletter_queue_name
    return self.queue_name + "-deadletter"

def bind_attributes(attributes):
    att_dict = {}
    for key, value in attributes.items():
        if isinstance(value, str):
            att_dict[key] = {"DataType": "String", "StringValue": value}
        elif isinstance(value, bytes):
            att_dict[key] = {"DataType": "Binary", "BinaryValue": value}
        elif isinstance(value, int) or isinstance(value, float):
            att_dict[key] = {"DataType": "Number", "StringValue": str(value)}
        elif isinstance(value, list):
            att_dict[key] = {"DataType": "String.Array", "StringValue": str(value)}
        elif isinstance(value, dict):
            att_dict[key] = {"DataType": "String.Map", "StringValue": str(value)}
        else:
            raise TypeError(
                f"Attribute value must be str, bytes, int, float or list, not {type(value)}."
            )
    return att_dict

def validate_message_attributes(attributes):
    if "source" not in attributes:
        raise ValueError("should have source key in messageAttributes")
    if "contains" not in attributes:
        raise ValueError("should have contains key in messageAttributes")
    if "event_type" not in attributes:
        raise ValueError("should have event_type key in messageAttributes")
    if "trace_id" not in attributes:
        attributes["trace_id"] = str(uuid.uuid4())
    return attributes