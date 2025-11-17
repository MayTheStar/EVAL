"""
Configuration Management
Centralized configuration for the RFP Analysis System.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional


class Config:
    """Configuration manager for RFP Analysis System."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            env_file: Path to .env file (loads default if None)
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        # API Keys
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        # Models
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
        self.chat_model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
        self.tokenizer_model = os.getenv("TOKENIZER_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        
        # Token Limits
        self.min_tokens = int(os.getenv("MIN_TOKENS", "512"))
        self.max_tokens = int(os.getenv("MAX_TOKENS", "1024"))
        
        # Retrieval Settings
        self.top_k_chunks = int(os.getenv("TOP_K_CHUNKS", "5"))
        self.max_response_tokens = int(os.getenv("MAX_RESPONSE_TOKENS", "1500"))
        
        # Directories
        self.default_output_dir = Path(os.getenv("OUTPUT_DIR", "output"))
        
        # Processing Settings
        self.batch_size = int(os.getenv("EMBEDDING_BATCH_SIZE", "100"))
        self.temperature = float(os.getenv("TEMPERATURE", "0.1"))
        
        # Validate required settings
        self._validate()
    
    def _validate(self):
        """Validate configuration."""
        if not self.openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please set it in .env file or environment variables."
            )
        
        if self.min_tokens >= self.max_tokens:
            raise ValueError(
                f"MIN_TOKENS ({self.min_tokens}) must be less than MAX_TOKENS ({self.max_tokens})"
            )
    
    def to_dict(self) -> dict:
        """Return configuration as dictionary."""
        return {
            "embedding_model": self.embedding_model,
            "chat_model": self.chat_model,
            "tokenizer_model": self.tokenizer_model,
            "min_tokens": self.min_tokens,
            "max_tokens": self.max_tokens,
            "top_k_chunks": self.top_k_chunks,
            "max_response_tokens": self.max_response_tokens,
            "default_output_dir": str(self.default_output_dir),
            "batch_size": self.batch_size,
            "temperature": self.temperature
        }
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        config_dict = self.to_dict()
        lines = ["Configuration:"]
        for key, value in config_dict.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)


# Global configuration instance
_config = None


def get_config(env_file: Optional[str] = None, reload: bool = False) -> Config:
    """
    Get global configuration instance.
    
    Args:
        env_file: Path to .env file
        reload: Force reload configuration
        
    Returns:
        Config instance
    """
    global _config
    
    if _config is None or reload:
        _config = Config(env_file)
    
    return _config


def set_config(config: Config):
    """
    Set global configuration instance.
    
    Args:
        config: Config instance to set
    """
    global _config
    _config = config


if __name__ == "__main__":
    # Test configuration
    config = get_config()
    print(config)