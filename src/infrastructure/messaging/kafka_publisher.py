from __future__ import annotations
import json
import structlog
from aiokafka import AIOKafkaProducer
from typing import Dict, Any

logger = structlog.get_logger(__name__)

class AIBackendEventPublisher:
    """
    Publishes AI analysis results back to the main backend via Kafka.
    """
    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.producer = None

    async def start(self):
        logger.info("Starting Kafka Producer", servers=self.bootstrap_servers)
        self.producer = AIOKafkaProducer(bootstrap_servers=self.bootstrap_servers)
        await self.producer.start()

    async def stop(self):
        if self.producer:
            logger.info("Stopping Kafka Producer")
            await self.producer.stop()

    async def publish_result(self, topic: str, task_id: str, payload: Dict[str, Any]):
        if not self.producer:
            raise RuntimeError("Producer not started")
            
        message = {
            "event_type": "AI_TASK_COMPLETED",
            "task_id": task_id,
            "data": payload
        }
        
        try:
            msg_bytes = json.dumps(message).encode("utf-8")
            await self.producer.send_and_wait(topic, msg_bytes, key=task_id.encode("utf-8"))
            logger.info("Successfully published AI result to Kafka", topic=topic, task_id=task_id)
        except Exception as e:
            logger.error("Failed to publish to Kafka", error=str(e), task_id=task_id)
            raise
