import pytest
import json
import sys
import os
from unittest.mock import patch, mock_open
from flask import Flask
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from create_embeddings import app  # Assuming your script is named 'app.py'

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

@patch("builtins.open", new_callable=mock_open, read_data="Sample file content")
@patch("create_embeddings.embed_file_content", return_value=[0.1, 0.2, 0.3])
@patch("create_embeddings.store_embeddings")
@patch("create_embeddings.create_faiss_index")
def test_upload_folder(mock_faiss, mock_store, mock_embed, mock_file, client):
    file_paths = ["test_file_1.txt", "test_file_2.pdf"]
    response = client.post("/api/upload_folder", 
                           data=json.dumps({"filePaths": file_paths}),
                           content_type="application/json")
    
    assert response.status_code == 200
    assert "Files processed, embeddings stored, and FAISS index created." in response.json["message"]
    
    # Ensure mocks were called correctly
    assert mock_embed.call_count == len(file_paths)
    mock_store.assert_called_once()
    mock_faiss.assert_called_once()

def test_upload_folder_no_files(client):
    response = client.post("/api/upload_folder", 
                           data=json.dumps({"filePaths": []}),
                           content_type="application/json")
    
    assert response.status_code == 400
    assert "No file paths provided" in response.json["error"]
