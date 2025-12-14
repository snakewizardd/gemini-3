import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    # API Keys (from environment variables)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    
    # Game settings
    num_games: int = 10
    save_images: bool = True
    output_dir: str = "results"
    
    # Model settings
    request_delay: float = 0.5  # Seconds between API calls
    max_retries: int = 3
    timeout: int = 30
    
    @classmethod
    def from_env(cls) -> 'Config':
        return cls(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            google_api_key=os.environ.get("GOOGLE_API_KEY"),
        )
