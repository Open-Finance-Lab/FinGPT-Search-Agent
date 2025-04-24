# create_embeddings.py
from dotenv import load_dotenv
import os
import openai
import pickle
import numpy as np
import faiss
import json
# OpenAI API key
load_dotenv()
api_key = os.getenv("API_KEY7")
openai.api_key = api_key

current_dir = os.path.dirname(os.path.abspath(__file__))
index_file = os.path.join(current_dir, 'faiss_index.idx')
embeddings_file = os.path.join(current_dir, 'embeddings.pkl')

# Helper function to generate embeddings
def embed_file_content(file_content):
    """
    Function to send file content to OpenAI's embedding API and get embeddings.
    """
    response = openai.Embedding.create(
        input=file_content,
        model="text-embedding-3-large"
    )
    return response['data'][0]['embedding']

# Helper function to store embeddings (pickling embeddings)
def store_embeddings(embeddings, file_paths):
    """
    Store the generated embeddings and file paths into a pickle file.
    """
    embeddings_data = {'file_paths': file_paths, 'embeddings': embeddings}
    with open(embeddings_file, 'wb') as f:
        pickle.dump(embeddings_data, f)

# Helper function to create a FAISS index
def create_faiss_index(chunks):
    """
    Create and store a FAISS index from the embeddings in `chunks`.
    Each item in `chunks` is expected to be a dict with key "embedding".
    """
    # Assume at least one chunk
    dimension = len(chunks[0]["embedding"])
    index = faiss.IndexFlatL2(dimension)  # L2 distance metric
    print("Creating index with dimension:", dimension)

    # Extract all embeddings into a NumPy array
    embeddings_np = np.array(
        [chunk["embedding"] for chunk in chunks], dtype='float32'
    )
    index.add(embeddings_np)
    print("Embeddings numpy shape:", embeddings_np.shape)

    # Store
    faiss.write_index(index, index_file)

def upload_folder(data):
    """
    Process incoming files and store chunk dictionaries (with text, metadata, embedding).
    """
    try:
        print("[DEBUG] Starting upload_folder with data:", data)

        # This will be your master list of chunk dictionaries
        chunks_list = []

        files = data.get('filePaths', [])
        print("[DEBUG] files array:", files)

        # Process each "file"
        for file_item in files:
            file_name = file_item.get('name')
            file_content = file_item.get('content')
            if file_name and file_content:
                print(f"[DEBUG] Processing file: {file_name}, length of content: {len(file_content)}")

                # Create the embedding for this file's content
                embedding = embed_file_content(file_content)

                # Build the chunk dictionary
                chunk_dict = {
                    "text": file_content,
                    "metadata": {
                        "file_path": file_name
                    },
                    "embedding": embedding
                }
                chunks_list.append(chunk_dict)

        # Now pickle the entire list
        with open(embeddings_file, 'wb') as f:
            pickle.dump(chunks_list, f)

        print("[DEBUG] Saved chunks to embeddings.pkl")

        # Create a FAISS index
        if len(chunks_list) > 0:
            create_faiss_index(chunks_list)
            print("[DEBUG] FAISS index created.")
        else:
            print("[DEBUG] No valid chunks found; not creating FAISS index.")

        return {"message": "Files processed, embeddings stored, and FAISS index created."}, 200

    except Exception as e:
        print(f"[DEBUG] Unexpected error in upload_folder: {str(e)}")
        return {"error": f"Server error: {str(e)}"}, 500
