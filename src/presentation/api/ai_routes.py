"""AI API endpoints for explainable repository discovery search."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Query
import structlog

from src.application.dtos.ai_market_brief_dto import MarketBriefResponseDTO
from src.application.dtos.ai_related_repo_dto import RelatedReposResponseDTO
from src.application.dtos.ai_repo_brief_dto import RepoBriefResponseDTO
from src.application.dtos.ai_repo_compare_dto import RepoCompareResponseDTO
from src.application.dtos.ai_search_dto import RepoSearchResponseDTO
from src.domain.exceptions import (
    AIInsightError,
    AISearchError,
    RepoInsightNotFoundError,
    ValidationError,
)
from src.infrastructure.config import Settings, get_settings

if TYPE_CHECKING:
    from src.application.use_cases.build_market_brief import BuildMarketBriefUseCase
    from src.application.use_cases.generate_repo_brief import GenerateRepoBriefUseCase
    from src.application.use_cases.generate_repo_compare import GenerateRepoCompareUseCase
    from src.application.use_cases.recommend_related_repositories import (
        RecommendRelatedRepositoriesUseCase,
    )
    from src.application.use_cases.search_repositories import SearchRepositoriesUseCase

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


def _get_search_use_case(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct the AI repository search use case for the request."""
    from src.application.use_cases.search_repositories import SearchRepositoriesUseCase
    from src.infrastructure.llm.ollama_embedding_service import OllamaEmbeddingService
    from src.infrastructure.storage.clickhouse_ai_service import ClickHouseAISearchService

    embedding_service: OllamaEmbeddingService | None = None
    if settings.ai_search_semantic_enabled:
        embedding_service = OllamaEmbeddingService(
            base_url=str(settings.ollama_base_url),
            model=settings.ollama_embedding_model,
            timeout_seconds=settings.ai_search_embedding_timeout_seconds,
        )

    return SearchRepositoriesUseCase(
        ClickHouseAISearchService(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        ),
        embedding_service=embedding_service,
        semantic_enabled=settings.ai_search_semantic_enabled,
        candidate_limit=settings.ai_search_candidate_limit,
    )


def _get_repo_brief_use_case(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct the AI repo brief use case for the request."""
    from src.application.use_cases.generate_repo_brief import GenerateRepoBriefUseCase
    from src.infrastructure.llm.ollama_generation_service import OllamaGenerationService
    from src.infrastructure.storage.clickhouse_ai_insights_service import (
        ClickHouseAIInsightsService,
    )

    generation_service: OllamaGenerationService | None = None
    if settings.ai_repo_brief_llm_enabled:
        generation_service = OllamaGenerationService(
            base_url=str(settings.ollama_base_url),
            model=settings.ollama_generation_model,
            timeout_seconds=settings.ai_repo_brief_timeout_seconds,
        )

    return GenerateRepoBriefUseCase(
        ClickHouseAIInsightsService(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        ),
        generation_service=generation_service,
        llm_enabled=settings.ai_repo_brief_llm_enabled,
    )


def _get_market_brief_use_case(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct the AI market brief use case for the request."""
    from src.application.use_cases.build_market_brief import BuildMarketBriefUseCase
    from src.infrastructure.llm.ollama_generation_service import OllamaGenerationService
    from src.infrastructure.storage.clickhouse_ai_insights_service import (
        ClickHouseAIInsightsService,
    )

    generation_service: OllamaGenerationService | None = None
    if settings.ai_market_brief_llm_enabled:
        generation_service = OllamaGenerationService(
            base_url=str(settings.ollama_base_url),
            model=settings.ollama_generation_model,
            timeout_seconds=settings.ai_repo_brief_timeout_seconds,
        )

    return BuildMarketBriefUseCase(
        ClickHouseAIInsightsService(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        ),
        generation_service=generation_service,
        llm_enabled=settings.ai_market_brief_llm_enabled,
    )


def _get_repo_compare_use_case(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct the AI repo compare use case for the request."""
    from src.application.use_cases.generate_repo_compare import GenerateRepoCompareUseCase
    from src.infrastructure.llm.ollama_generation_service import OllamaGenerationService
    from src.infrastructure.storage.clickhouse_ai_insights_service import (
        ClickHouseAIInsightsService,
    )

    generation_service: OllamaGenerationService | None = None
    if settings.ai_repo_brief_llm_enabled:
        generation_service = OllamaGenerationService(
            base_url=str(settings.ollama_base_url),
            model=settings.ollama_generation_model,
            timeout_seconds=settings.ai_repo_brief_timeout_seconds,
        )

    return GenerateRepoCompareUseCase(
        ClickHouseAIInsightsService(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        ),
        generation_service=generation_service,
        llm_enabled=settings.ai_repo_brief_llm_enabled,
    )


def _get_related_repos_use_case(
    settings: Annotated[Settings, Depends(get_settings)],
) -> object:
    """Construct the related repository recommendation use case for the request."""
    from src.application.use_cases.recommend_related_repositories import (
        RecommendRelatedRepositoriesUseCase,
    )
    from src.infrastructure.storage.clickhouse_ai_insights_service import (
        ClickHouseAIInsightsService,
    )
    from src.infrastructure.storage.clickhouse_ai_service import ClickHouseAISearchService

    insights_service = ClickHouseAIInsightsService(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        user=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=settings.clickhouse_database,
    )
    return RecommendRelatedRepositoriesUseCase(
        insights_service,
        ClickHouseAISearchService(
            host=settings.clickhouse_host,
            port=settings.clickhouse_port,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
            database=settings.clickhouse_database,
        ),
        candidate_limit=settings.ai_search_candidate_limit,
    )


@router.get("/search", response_model=RepoSearchResponseDTO)
async def search_repositories(
    settings: Annotated[Settings, Depends(get_settings)],
    use_case: Annotated[object, Depends(_get_search_use_case)],
    query: Annotated[str, Query(min_length=2, max_length=200)],
    category: Annotated[str | None, Query()] = None,
    language: Annotated[str | None, Query(max_length=40)] = None,
    min_stars: Annotated[int, Query(ge=0, le=2_000_000)] = 10_000,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int | None, Query(ge=1, le=20)] = None,
) -> RepoSearchResponseDTO:
    """Return explainable repository search results for a natural-language query."""

    search_use_case = cast("SearchRepositoriesUseCase", use_case)
    try:
        return await search_use_case.execute(
            query=query,
            category=category,
            primary_language=language,
            min_stars=min_stars,
            days=days,
            limit=limit or settings.ai_search_default_limit,
        )
    except ValidationError as exc:
        logger.warning("ai.search_validation_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except AISearchError as exc:
        logger.error("ai.search_failed", error=str(exc))
        raise HTTPException(status_code=503, detail="AI search unavailable") from exc


@router.get("/market-brief", response_model=MarketBriefResponseDTO)
async def get_market_brief(
    use_case: Annotated[object, Depends(_get_market_brief_use_case)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    breakout_limit: Annotated[int, Query(ge=1, le=8)] = 3,
    category_limit: Annotated[int, Query(ge=1, le=8)] = 2,
    topic_limit: Annotated[int, Query(ge=1, le=12)] = 3,
) -> MarketBriefResponseDTO:
    """Return a grounded AI market brief for the selected time window."""
    market_brief_use_case = cast("BuildMarketBriefUseCase", use_case)
    try:
        return await market_brief_use_case.execute(
            days=days,
            breakout_limit=breakout_limit,
            category_limit=category_limit,
            topic_limit=topic_limit,
        )
    except AIInsightError as exc:
        logger.error("ai.market_brief_failed", days=days, error=str(exc))
        raise HTTPException(status_code=503, detail="AI market brief unavailable") from exc


@router.get("/repo-brief", response_model=RepoBriefResponseDTO)
async def get_repo_brief(
    use_case: Annotated[object, Depends(_get_repo_brief_use_case)],
    repo_name: Annotated[
        str,
        Query(
            min_length=3,
            pattern=r"^[^/]+/[^/]+$",
            description="Repository in owner/repo format",
        ),
    ],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> RepoBriefResponseDTO:
    """Return a grounded repo brief and why-trending narrative."""
    repo_brief_use_case = cast("GenerateRepoBriefUseCase", use_case)
    try:
        return await repo_brief_use_case.execute(repo_name=repo_name, days=days)
    except RepoInsightNotFoundError as exc:
        logger.warning("ai.repo_brief_not_found", repo_name=repo_name, error=str(exc))
        raise HTTPException(status_code=404, detail="Repository not found") from exc
    except AIInsightError as exc:
        logger.error("ai.repo_brief_failed", repo_name=repo_name, error=str(exc))
        raise HTTPException(status_code=503, detail="AI repo brief unavailable") from exc


@router.get("/repo-compare", response_model=RepoCompareResponseDTO)
async def get_repo_compare(
    use_case: Annotated[object, Depends(_get_repo_compare_use_case)],
    base_repo_name: Annotated[
        str,
        Query(
            min_length=3,
            pattern=r"^[^/]+/[^/]+$",
            description="Base repository in owner/repo format",
        ),
    ],
    compare_repo_name: Annotated[
        str,
        Query(
            min_length=3,
            pattern=r"^[^/]+/[^/]+$",
            description="Comparison repository in owner/repo format",
        ),
    ],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> RepoCompareResponseDTO:
    """Return a grounded comparison between two repositories."""
    repo_compare_use_case = cast("GenerateRepoCompareUseCase", use_case)
    try:
        return await repo_compare_use_case.execute(
            base_repo_name=base_repo_name,
            compare_repo_name=compare_repo_name,
            days=days,
        )
    except ValidationError as exc:
        logger.warning(
            "ai.repo_compare_validation_failed",
            base_repo_name=base_repo_name,
            compare_repo_name=compare_repo_name,
            error=str(exc),
        )
        raise HTTPException(status_code=422, detail=exc.message) from exc
    except RepoInsightNotFoundError as exc:
        logger.warning(
            "ai.repo_compare_not_found",
            base_repo_name=base_repo_name,
            compare_repo_name=compare_repo_name,
            error=str(exc),
        )
        raise HTTPException(status_code=404, detail="Repository not found") from exc
    except AIInsightError as exc:
        logger.error(
            "ai.repo_compare_failed",
            base_repo_name=base_repo_name,
            compare_repo_name=compare_repo_name,
            error=str(exc),
        )
        raise HTTPException(status_code=503, detail="AI repo compare unavailable") from exc


@router.get("/related-repos", response_model=RelatedReposResponseDTO)
async def get_related_repositories(
    use_case: Annotated[object, Depends(_get_related_repos_use_case)],
    repo_name: Annotated[
        str,
        Query(
            min_length=3,
            pattern=r"^[^/]+/[^/]+$",
            description="Source repository in owner/repo format",
        ),
    ],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    limit: Annotated[int, Query(ge=1, le=12)] = 6,
) -> RelatedReposResponseDTO:
    """Return repositories related to the provided source repository."""
    related_repos_use_case = cast("RecommendRelatedRepositoriesUseCase", use_case)
    try:
        return await related_repos_use_case.execute(
            repo_name=repo_name,
            days=days,
            limit=limit,
        )
    except RepoInsightNotFoundError as exc:
        logger.warning("ai.related_repos_not_found", repo_name=repo_name, error=str(exc))
        raise HTTPException(status_code=404, detail="Repository not found") from exc
    except AIInsightError as exc:
        logger.error("ai.related_repos_failed", repo_name=repo_name, error=str(exc))
        raise HTTPException(status_code=503, detail="AI related repos unavailable") from exc
