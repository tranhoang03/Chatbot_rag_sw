import os
from dotenv import load_dotenv
from dataclasses import dataclass
from pathlib import Path
# import streamlit as st # Removed import as st.secrets is no longer used

# Load environment variables
load_dotenv()

@dataclass
class Config:
    """Configuration for RAG system"""
    # Base directory
    base_dir: Path = Path(__file__).parent
    
    # Server configuration
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", 5000))
    
    # Database configuration
    db_path: str = os.getenv("DB_PATH", "Database.db")
    db_timeout: int = int(os.getenv("DB_TIMEOUT", 30))
    
    # Vector store configuration
    vector_store_dir: str = "search_engine/vector_store"
    vector_store_path: str = os.getenv("VECTOR_STORE_PATH", str(base_dir / vector_store_dir))
    vector_index_file: str = "index.faiss"
    vector_metadata_file: str = "index.pkl"
    vector_index_path: str = str(base_dir / vector_store_dir / vector_index_file)
    vector_metadata_path: str = str(base_dir / vector_store_dir / vector_metadata_file)
    top_k_results: int = int(os.getenv("TOP_K_RESULTS", 3))
    
    # Description vector store configuration
    description_store_dir: str = "search_engine/description_store"
    description_vector_store_path: str = os.getenv("DESCRIPTION_VECTOR_STORE_PATH", str(base_dir / description_store_dir))
    description_index_file: str = "description_index.faiss"
    description_metadata_file: str = "description_index.pkl"
    description_index_path: str = str(base_dir / description_store_dir / description_index_file)
    description_metadata_path: str = str(base_dir / description_store_dir / description_metadata_file)
    
    # Model configuration
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "vinai/phobert-base")
    _model: str = os.getenv("LLM_MODEL", "gemini-1.5-flash-latest")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", 0))
    
    # Image search configuration
    image_batch_size: int = int(os.getenv("IMAGE_BATCH_SIZE", 32))
    image_index_dir: str = "search_engine/image_index"
    image_index_path: str = os.getenv("IMAGE_FAISS_INDEX_PATH", str(base_dir / image_index_dir / "index.faiss"))
    image_metadata_path: str = os.getenv("IMAGE_FAISS_METADATA_PATH", str(base_dir / image_index_dir / "metadata.pkl"))
    
    # System configuration
    system_dir: str = "system"
    chat_history_file: str = "chat_histories.json"
    chat_history_path: str = str(base_dir / chat_history_file)
    max_history_per_user: int = int(os.getenv("MAX_HISTORY_PER_USER", 3))
    
    # API Keys - Read directly from environment variables (loaded from .env)
    google_api_key: str = os.getenv("GOOGLE_API_KEY")
    huggingface_hub_token: str = os.getenv("HUGGINGFACE_HUB_TOKEN")
    
    def __post_init__(self):
        """Ensure paths exist and essential keys are loaded"""
        # Ensure vector store directory exists
        os.makedirs(self.vector_store_path, exist_ok=True)
        if not os.path.exists(self.vector_index_path):
            print(f"Warning: Vector index not found at {self.vector_index_path}")
        if not os.path.exists(self.vector_metadata_path):
            print(f"Warning: Vector metadata not found at {self.vector_metadata_path}")

        # Ensure description vector store directory exists
        os.makedirs(self.description_vector_store_path, exist_ok=True)
        if not os.path.exists(self.description_index_path):
            print(f"Warning: Description index not found at {self.description_index_path}")
        if not os.path.exists(self.description_metadata_path):
            print(f"Warning: Description metadata not found at {self.description_metadata_path}")

        # Ensure image index directory exists
        os.makedirs(os.path.dirname(self.image_index_path), exist_ok=True)
        if not os.path.exists(self.image_index_path):
            print(f"Warning: Image index not found at {self.image_index_path}")
        if not os.path.exists(self.image_metadata_path):
            print(f"Warning: Image metadata not found at {self.image_metadata_path}")

        # Ensure db path is absolute
        db_full_path = os.path.join(self.base_dir, self.db_path)
        if not os.path.exists(db_full_path):
            raise ValueError(f"Database file not found at {db_full_path}")
        self.db_path = db_full_path

        # --- Check if keys were loaded from environment --- 
        if not self.google_api_key:
             print("ERROR: GOOGLE_API_KEY not found in environment variables (check .env file). Application might fail.")
        else:
             print("Loaded GOOGLE_API_KEY from environment.")
             
        if not self.huggingface_hub_token:
             print("WARNING: HUGGINGFACE_HUB_TOKEN not found in environment variables (check .env file). Model downloads might be rate-limited or fail if not cached.")
        else:
             print("Loaded HUGGINGFACE_HUB_TOKEN from environment.")
 

