import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.usecases.process_ai_task import ProcessAITaskUseCase
from src.domain.entities.ai_task import AITask

@pytest.fixture
def usecase():
    llm = AsyncMock()
    llm.generate_completion.return_value = "Great project!"
    vector = AsyncMock()
    github = AsyncMock()
    github.fetch_repo_details.return_value = {"readme": "Test Readme", "stars": 100}
    return ProcessAITaskUseCase(llm, vector, github)

@pytest.mark.asyncio
async def test_process_ai_task_success(usecase):
    task = AITask(task_id="123", repository_url="https://github.com/test/test")
    result = await usecase.execute(task)
    
    assert result.status == "completed"
    assert result.result_summary == "Great project!"
    usecase.github_client.fetch_repo_details.assert_called_once()
