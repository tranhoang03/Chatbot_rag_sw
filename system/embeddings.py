from langchain_core.embeddings import Embeddings 
from transformers import AutoModel, AutoTokenizer
import torch
from typing import List

class PhoBERTEmbeddings(Embeddings):
    def __init__(self, model_name: str = "vinai/phobert-base"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.max_length = 256 

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=self.max_length)
            with torch.no_grad():
                outputs = self.model(**inputs)
            mean_emb = outputs.last_hidden_state.mean(dim=1).squeeze(0).numpy() 
            embeddings.append(mean_emb.tolist())
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=self.max_length)
        with torch.no_grad():
            outputs = self.model(**inputs)
        mean_emb = outputs.last_hidden_state.mean(dim=1).squeeze(0).numpy()
        return mean_emb.tolist() 