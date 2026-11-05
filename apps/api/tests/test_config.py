from pathlib import Path

from app.core.config import Settings


def test_default_chat_model_is_gemini_2_5_flash() -> None:
    assert Settings().default_chat_model == "gemini-2.5-flash"


def test_env_example_keeps_gemini_2_5_flash_chat_model() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    env_example = repo_root / ".env.example"

    assert "DEFAULT_CHAT_MODEL=gemini-2.5-flash" in env_example.read_text()
