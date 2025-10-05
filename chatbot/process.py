######################################################################################################################
######################################################################################################################

import numpy as np
import faiss
import pickle
import logging
from sentence_transformers import SentenceTransformer
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity
import os
import logging
from config.config_file import DATA_DIR,LOGS_DIR 


######################################################################################################################
######################################################################################################################

logger = logging.getLogger(__name__)

######################################################################################################################
######################################################################################################################

def chunk_paragraphs(file_path, chunk_size=100):
    """
    Reads a plain text file, splits it into paragraphs, and creates chunks of specified max size (in characters).
    """
    try:
        logger.info(f"Chunking paragraphs from {file_path}")
        
        # Read the file as plain text
        with open(file_path, 'r', encoding='utf-8') as file:
            data = file.read()
        
        # Split text into paragraphs by newlines
        paragraphs = [p.strip() for p in data.split("\n") if p.strip()]
        
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # Add paragraph to current chunk if size allows
            if len(current_chunk) + len(paragraph) + 1 <= chunk_size:  # +1 for space
                current_chunk += " " + paragraph if current_chunk else paragraph
            else:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
        
        # Add last chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(f"Successfully chunked {len(chunks)} paragraphs.")
        logger.debug(f"Chunks: {chunks}")
        return chunks
    
    except Exception as e:
        logger.error(f"Error chunking paragraphs: {e}")
        raise

######################################################################################################################
######################################################################################################################


def create_faiss_index(chunks, model_name='all-MiniLM-L6-v2'):
    try:
        logger.info("Creating FAISS index...")
        model = SentenceTransformer(model_name)
        embeddings = model.encode(chunks, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings)
        logger.info(f"FAISS index created with {index.ntotal} vectors.")
        return index, embeddings
    except Exception as e:
        logger.error(f"Error creating FAISS index: {e}")
        raise


######################################################################################################################
######################################################################################################################

def save_index_and_embeddings(index, embeddings, chunks):
    try:
        logger.info("Saving FAISS index and embeddings...")
        faiss.write_index(index, "faiss_index.index")
        with open("embeddings.pkl", "wb") as f:
            pickle.dump(embeddings, f)
        with open("chunks.pkl", "wb") as f:
            pickle.dump(chunks, f)
        logger.info("FAISS index and embeddings saved successfully.")
    except Exception as e:
        logger.error(f"Error saving FAISS index or embeddings: {e}")
        raise

######################################################################################################################
######################################################################################################################


def load_index_and_embeddings():
    try:
        logger.info("Loading FAISS index and embeddings...")
        index = faiss.read_index("faiss_index.index")
        with open("embeddings.pkl", "rb") as f:
            embeddings = pickle.load(f)
        with open("chunks.pkl", "rb") as f:
            chunks = pickle.load(f)
        logger.info("FAISS index and embeddings loaded successfully.")
        return index, embeddings, chunks
    except Exception as e:
        logger.error(f"Error loading FAISS index or embeddings: {e}")
        raise



######################################################################################################################
######################################################################################################################

def hybrid_search(query, index, model, corpus,embeddings, k=3):
    
    results = {}
    logger.info("Hybrid Search is Processing")
    try:
        # Encode query
        query_embedding = model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)

        # --- 1. FAISS Semantic Search ---
        scores, indices = index.search(query_embedding, k)
        faiss_results = [(corpus[i], float(scores[0][j])) for j, i in enumerate(indices[0])]
        results["faiss"] = faiss_results

        # --- 2. BM25 Keyword Search ---
        tokenized_corpus = [doc.split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        bm25_scores = bm25.get_scores(query.split())
        bm25_topk = np.argsort(bm25_scores)[::-1][:k]
        bm25_results = [(corpus[i], float(bm25_scores[i])) for i in bm25_topk]
        results["bm25"] = bm25_results

        # --- 3. Cosine Similarity Search ---
        cos_scores = cosine_similarity(query_embedding, embeddings)[0]
        topk_indices = np.argsort(cos_scores)[::-1][:k]
        cos_results = [(corpus[i], float(cos_scores[i])) for i in topk_indices]
        results["cosine"] = cos_results

        return results

    except Exception as e:
        logger.error(f"Error during hybrid search: {e}")
        raise

######################################################################################################################
######################################################################################################################


def start_process():
    try:
        # Step 1: Chunk the JSON file

        chunks = chunk_paragraphs(os.path.join(DATA_DIR, "merged_file.md"))

        # Step 2: Create FAISS index
        model = SentenceTransformer('all-MiniLM-L6-v2')
        index, embeddings = create_faiss_index(chunks)

        # Step 3: Save the index and embeddings
        save_index_and_embeddings(index, embeddings, chunks)

        return index, model, chunks, embeddings

    except Exception as e:
        logger.error(f"An error occurred in the main process: {e}")
        return {"status": "error", "message": str(e)}
    
######################################################################################################################
######################################################################################################################

