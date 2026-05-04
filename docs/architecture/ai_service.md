# AI Service Architecture Guide

## Overview
The AI Service is a dedicated microservice in the `Github-Analyzer` ecosystem designed to perform intelligent analysis on repository metadata, code snippets, and pull requests.

## Technology Stack
- **Framework**: FastAPI (Python 3.14)
- **LLM Engine**: Ollama (Running local Llama3)
- **Vector DB**: Qdrant
- **Messaging**: 
  - Redis Streams (for incoming tasks)
  - Kafka (for publishing results back to the main backend)
- **Monitoring**: Prometheus & Grafana

## Architecture (Clean Architecture)
Dependency flow strictly points inward.

1. **Domain Layer** (`src/domain`): Contains core `AITask` entities, Enums, and domain-specific exceptions.
2. **Application Layer** (`src/application`): Houses the `ProcessAITaskUseCase` which acts as the orchestrator. It does not know about FastAPI or HTTP.
3. **Infrastructure Layer** (`src/infrastructure`): Contains concrete implementations for `OllamaAdapter`, `QdrantStore`, `KafkaPublisher`, and `RedisConsumer`.
4. **Presentation Layer** (`src/presentation`): FastAPI endpoints acting as controllers.

## Component Interaction Flow
1. User requests analysis via Backend.
2. Backend pushes task ID to Redis Stream.
3. `RedisConsumer` in AI Service picks up the task.
4. `ProcessAITaskUseCase` is invoked:
   - Fetches Repo Data.
   - Embeds data into `QdrantStore`.
   - Sends prompt to `OllamaAdapter`.
5. Upon completion, `KafkaPublisher` fires an event `AI_TASK_COMPLETED`.
6. Backend updates DB and notifies Frontend via WebSockets.

## Error Handling
All external calls use the `tenacity` library for exponential backoff retries. Timeouts are explicitly handled via `httpx.TimeoutException` mapped to `ModelTimeoutError`.
