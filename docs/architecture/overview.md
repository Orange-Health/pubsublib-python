# Architecture Overview

`pubsublib` is a Python library that provides a unified, opinionated abstraction layer over AWS SNS (Simple Notification Service) and AWS SQS (Simple Queue Service) for Orange Health's event-driven microservices architecture.

---

## Purpose

Services within the Orange Health platform communicate asynchronously via events. Rather than each service integrating directly with the AWS SDK, `pubsublib` encapsulates all publish/subscribe concerns:

- Topic and queue lifecycle management
- Message publishing (standard and FIFO)
- Message consumption with handler callbacks
- Transparent payload compression (gzip + base64)
- Large-message offloading via Redis
- Message integrity verification (MD5)
- IAM policy wiring between SNS topics and SQS queues

---

## High-Level Component Diagram

```mermaid
graph TD
    subgraph Consumer["Consumer Service"]
        APP["Application Code"]
    end

    subgraph pubsublib["pubsublib (this library)"]
        ADAPTER["AWSPubSubAdapter\n(aws/main.py)"]
        CACHE["CacheAdapter\n(common/cache_adapter.py)"]
        CODEC["Codec\n(common/codec.py)"]
        HELPER["Helpers\n(aws/utils/helper.py)"]
    end

    subgraph AWS["AWS"]
        SNS["SNS Topics\n(Standard / FIFO)"]
        SQS["SQS Queues\n(Standard / FIFO)"]
    end

    subgraph External["External Infrastructure"]
        REDIS["Redis\n(large-message store)"]
    end

    APP -->|publish / create / subscribe / poll| ADAPTER
    ADAPTER --> CODEC
    ADAPTER --> HELPER
    ADAPTER --> CACHE
    ADAPTER -->|boto3 SNS API| SNS
    ADAPTER -->|boto3 SQS API| SQS
    SNS -->|fanout| SQS
    CACHE <-->|PUBSUB: prefix| REDIS
```

---

## Module Map

| Path | Responsibility |
|---|---|
| `src/pubsublib/aws/main.py` | `AWSPubSubAdapter` — primary public interface |
| `src/pubsublib/aws/utils/helper.py` | Attribute binding, validation, MD5 integrity, large-message detection |
| `src/pubsublib/aws/exceptions.py` | Custom exception types (`InvalidMessageAttributesDefinition`) |
| `src/pubsublib/common/cache_adapter.py` | Redis wrapper (`CacheAdapter`) with `PUBSUB:` key prefix |
| `src/pubsublib/common/codec.py` | gzip compression + base64 encode/decode utilities |

---

## Message Flow: Publishing

```mermaid
sequenceDiagram
    participant Caller
    participant AWSPubSubAdapter
    participant Codec
    participant CacheAdapter
    participant Redis
    participant SNS

    Caller->>AWSPubSubAdapter: publish_message(topic_arn, message, attributes, is_fifo)
    AWSPubSubAdapter->>AWSPubSubAdapter: validate required attributes\n(source, contains, event_type, trace_id)

    alt compress_enabled
        AWSPubSubAdapter->>Codec: gzip_and_b64(message)
        Codec-->>AWSPubSubAdapter: b64_compressed_string
        AWSPubSubAdapter->>AWSPubSubAdapter: set attributes["compress"] = "true"
    end

    alt message > 64 KB
        AWSPubSubAdapter->>CacheAdapter: set(uuid_key, message, TTL=14400min)
        CacheAdapter->>Redis: SET PUBSUB:<uuid> value EX ttl
        AWSPubSubAdapter->>AWSPubSubAdapter: set attributes["redis_key"] = uuid_key
    end

    AWSPubSubAdapter->>SNS: publish(TopicArn, Message, MessageAttributes)
    SNS-->>AWSPubSubAdapter: MessageId
    AWSPubSubAdapter-->>Caller: MessageId
```

---

## Message Flow: Consuming

```mermaid
sequenceDiagram
    participant Caller
    participant AWSPubSubAdapter
    participant SQS
    participant CacheAdapter
    participant Redis
    participant Codec
    participant Handler

    Caller->>AWSPubSubAdapter: poll_message_from_queue(queue_url, handler)
    AWSPubSubAdapter->>SQS: receive_message(...)
    SQS-->>AWSPubSubAdapter: Messages[]

    loop For each message
        AWSPubSubAdapter->>AWSPubSubAdapter: MD5 integrity check

        alt redis_key present in MessageAttributes
            AWSPubSubAdapter->>CacheAdapter: get(redis_key)
            CacheAdapter->>Redis: GET PUBSUB:<key>
            Redis-->>CacheAdapter: payload
            CacheAdapter-->>AWSPubSubAdapter: payload
            AWSPubSubAdapter->>AWSPubSubAdapter: replace Body.Message with Redis payload
        end

        alt compress attribute == "true"
            AWSPubSubAdapter->>Codec: b64_decode_and_gunzip_if(message, True)
            Codec-->>AWSPubSubAdapter: decompressed bytes
        end

        AWSPubSubAdapter->>Handler: handler(message)
        Handler-->>AWSPubSubAdapter: True (ack) | False (nack)

        alt handler returns True
            AWSPubSubAdapter->>SQS: delete_message(ReceiptHandle)
        end
    end
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| SNS → SQS fanout pattern | Decouples producers from consumers; multiple services can subscribe to the same topic |
| Redis large-message offload (>64 KB) | AWS SNS/SQS payload limit is 256 KB; Redis offloading keeps message headers small and transport fast |
| gzip + base64 compression | JSON event payloads compress well; base64 ensures the binary output is SNS-safe (text transport) |
| Required attributes: `source`, `contains`, `event_type` | Provides a consistent event envelope for routing, filtering, and observability |
| `trace_id` auto-generation | Ensures every event can be correlated across services even if the caller doesn't supply one |
| FIFO support | Ordered delivery for use cases requiring strict event sequencing |
| Handler-based ack model | Consumer logic is decoupled from the transport; returning `True` deletes the message |

---

## Runtime Dependencies

| Package | Usage |
|---|---|
| `boto3` / `botocore` | AWS SDK — SNS and SQS API calls |
| `redis` | Large-message body offloading and retrieval |

Python ≥ 3.8 is required.
