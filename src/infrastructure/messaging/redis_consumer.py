from __future__ import annotations
import asyncio
import json
import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)

class AIRedisStreamConsumer:
    """
    Consumes tasks from a Redis Stream.
    Uses consumer groups to distribute load among multiple AI worker instances.
    """
    def __init__(self, redis_url: str, stream_name: str, group_name: str):
        self.redis = Redis.from_url(redis_url)
        self.stream_name = stream_name
        self.group_name = group_name
        self.consumer_name = f"ai_worker_{id(self)}"

    async def initialize_group(self):
        try:
            await self.redis.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
            logger.info("Created Redis consumer group", group=self.group_name)
        except Exception as e:
            if "BUSYGROUP" in str(e):
                logger.debug("Consumer group already exists")
            else:
                raise

    async def consume_loop(self, handler_callback):
        logger.info("Starting Redis consumption loop", stream=self.stream_name)
        await self.initialize_group()
        
        while True:
            try:
                # Block for 5 seconds waiting for new messages
                messages = await self.redis.xreadgroup(
                    self.group_name, self.consumer_name, {self.stream_name: ">"}, count=1, block=5000
                )
                
                for stream, msg_list in messages:
                    for message_id, msg_data in msg_list:
                        logger.info("Received task from Redis", msg_id=message_id)
                        
                        # Process message
                        payload = {k.decode(): v.decode() for k, v in msg_data.items()}
                        await handler_callback(payload)
                        
                        # Acknowledge
                        await self.redis.xack(self.stream_name, self.group_name, message_id)
                        
            except asyncio.CancelledError:
                logger.info("Consumption loop cancelled")
                break
            except Exception as e:
                logger.error("Error in Redis consumer loop", error=str(e))
                await asyncio.sleep(2)
