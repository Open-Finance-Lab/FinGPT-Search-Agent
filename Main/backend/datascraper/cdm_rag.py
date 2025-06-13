# cdm_rag.py
from dotenv import load_dotenv
import os
# import re
import pickle
import numpy as np
import faiss
import openai
import ast  # For Python code parsing
import markdown  # For Markdown parsing
import logging

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Global variables for index and embeddings
index = None
all_chunks = None

current_dir = os.path.dirname(os.path.abspath(__file__))

def initialize_rag():
    """
    Initializes the RAG components by loading the FAISS index and chunk list.
    """
    global index, all_chunks
    index_file = os.path.join(current_dir, 'faiss_index.idx')
    embeddings_file = os.path.join(current_dir, 'embeddings.pkl')

    if os.path.exists(index_file) and os.path.exists(embeddings_file):
        # Load FAISS index
        index = faiss.read_index(index_file)

        # Load chunks list (with text, metadata, embedding)
        with open(embeddings_file, 'rb') as f:
            all_chunks = pickle.load(f)

        print("Loaded existing FAISS index and chunk data.")
    else:
        missing = []
        if not os.path.exists(index_file):
            missing.append(index_file)
        if not os.path.exists(embeddings_file):
            missing.append(embeddings_file)
        raise FileNotFoundError(f"Missing files for RAG: {', '.join(missing)}")

def load_index_and_embeddings(index_file='faiss_index.idx', embeddings_file='embeddings.pkl'):
    """
    Loads the FAISS index and embeddings with metadata from disk.
    """
    index = faiss.read_index(index_file)
    with open(embeddings_file, 'rb') as f:
        embeddings_data = pickle.load(f)
        embeddings = embeddings_data['embeddings']

    return index, embeddings

def embed_query(query, model="text-embedding-3-large"):
    """
    Generates an embedding for the query text.
    """
    # response = openai.Embedding.create(
    #     input=query,
    #     model=model
    # )
    # return response['data'][0]['embedding']
    response = openai.Embedding.create(
        input=query,
        model=model
    )
    return response['data'][0]['embedding']


def retrieve_chunks(query, k=1):
    """
    Retrieves the most relevant chunks for a given query.
    """
    global index, all_chunks
    if index is None or all_chunks is None:
        initialize_rag()

    # Prepare the query vector
    query_embedding = embed_query(query)
    query_vector = np.array([query_embedding], dtype='float32')
    faiss.normalize_L2(query_vector)  # Normalizing if index was built from normalized embeddings

    # Search
    distances, idxs = index.search(query_vector, k)
    # idxs is shape (1, k), e.g. [[1, 10, 0, ...]]

    # Map each index to the chunk in `all_chunks`
    results = [all_chunks[i] for i in idxs[0]]
    return results

def generate_answer(query, relevant_chunks, model_name):
    """
    Generates an answer to the query using the specified model and the relevant context.
    """
    # Build a string context from the chunk data
    context = ""
    for chunk in relevant_chunks:
        file_path = chunk['metadata']['file_path']
        text = chunk['text']
        context += f"File: {file_path}\nContent:\n{text}\n\n"

    # prompt
    prompt = f"""You are a helpful financial advisor providing detailed and accurate answers.
    
Context:
{context}

Question:
{query}

Answer as thoroughly as possible based on the context provided."""

    # Use OpenAI's model
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[
            {'role': 'user', 'content': 'You are a helpful financial advisor providing detailed and accurate answers.' + prompt}
        ],
        temperature=1,  # Lower temperature for more precise answers
        max_completion_tokens=1500  # Adjust as necessary
    )

    answer = response['choices'][0]['message']['content']
    return answer.strip()

def get_rag_response(question, model_name="o1-preview"):
    """
    Generates a response using the RAG pipeline with the specified model.
    """
    if index is None or all_chunks is None:
        initialize_rag()

        # 1. Retrieve relevant chunks
    relevant_chunks = retrieve_chunks(question, k=1)

    # 2. Log them
    logging.info("\nRetrieved Chunks:")
    for i, chunk in enumerate(relevant_chunks, start=1):
        logging.info(f"Chunk {i}:")
        logging.info(f"File: {chunk['metadata']['file_path']}")
        logging.info(f"Content:\n{chunk['text']}")

    # 3. Generate an answer
    answer = generate_answer(question, relevant_chunks, model_name)
    return answer


def get_rag_advanced_response(question, model_name="o1-preview"):
    """
    Generates an advanced response using the RAG pipeline.
    """
    # For simplicity, we'll use the same as get_rag_response
    return get_rag_response(question, model_name)