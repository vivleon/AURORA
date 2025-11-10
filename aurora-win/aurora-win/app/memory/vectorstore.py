import faiss, numpy as np

def init_index(dim: int = 768):
    index = faiss.IndexFlatL2(dim)
    return index
