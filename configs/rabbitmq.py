import asyncio
import json
from typing import Any

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message
from aio_pika.abc import (
    AbstractChannel,
    AbstractExchange,
    AbstractQueue,
    AbstractRobustConnection,
)

from configs.settings import (
    RABBITMQ_PREFETCH_COUNT,
    RABBITMQ_URL,
    RABBITMQ_REGISTRATION_SYNC_EXCHANGE,
    RABBITMQ_REGISTRATION_SYNC_QUEUE,
    RABBITMQ_REGISTRATION_SYNC_ROUTING_KEY,
)

_connection: AbstractRobustConnection | None = None
_channel: AbstractChannel | None = None
_sync_exchange: AbstractExchange | None = None
_sync_queue: AbstractQueue | None = None
_lock = asyncio.Lock()


async def _ensure_rabbitmq() -> tuple[AbstractChannel, AbstractExchange, AbstractQueue]:
    global _connection, _channel, _sync_exchange, _sync_queue

    if _connection and not _connection.is_closed and _channel and not _channel.is_closed:
        if _sync_exchange is not None and _sync_queue is not None:
            return _channel, _sync_exchange, _sync_queue

    async with _lock:
        if _connection is None or _connection.is_closed:
            _connection = await aio_pika.connect_robust(RABBITMQ_URL)

        if _channel is None or _channel.is_closed:
            _channel = await _connection.channel()
            await _channel.set_qos(prefetch_count=RABBITMQ_PREFETCH_COUNT)

        if _sync_exchange is None:
            _sync_exchange = await _channel.declare_exchange(
                RABBITMQ_REGISTRATION_SYNC_EXCHANGE,
                ExchangeType.DIRECT,
                durable=True,
            )

        if _sync_queue is None:
            _sync_queue = await _channel.declare_queue(
                RABBITMQ_REGISTRATION_SYNC_QUEUE,
                durable=True,
            )
            await _sync_queue.bind(_sync_exchange, routing_key=RABBITMQ_REGISTRATION_SYNC_ROUTING_KEY)

    return _channel, _sync_exchange, _sync_queue


async def _publish_json_message(
    exchange: AbstractExchange,
    routing_key: str,
    payload: dict[str, Any],
    message_id: str,
    headers: dict[str, Any] | None = None,
) -> None:
    message = Message(
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
        delivery_mode=DeliveryMode.PERSISTENT,
        message_id=message_id,
        headers=headers,
    )
    await exchange.publish(message, routing_key=routing_key)


async def publish_registration_sync_message(payload: dict[str, Any], message_id: str) -> None:
    await _ensure_rabbitmq()
    global _sync_exchange
    if _sync_exchange:
        await _publish_json_message(
            exchange=_sync_exchange,
            routing_key=RABBITMQ_REGISTRATION_SYNC_ROUTING_KEY,
            payload=payload,
            message_id=message_id,
        )


async def close_rabbitmq() -> None:
    global _connection, _channel, _sync_exchange, _sync_queue

    if _channel is not None and not _channel.is_closed:
        await _channel.close()
    if _connection is not None and not _connection.is_closed:
        await _connection.close()

    _connection = None
    _channel = None
    _sync_exchange = None
    _sync_queue = None
