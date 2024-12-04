#!/bin/bash
if ! command -v pip &> /dev/null; then
    echo "pip could not be found. Installing pip..."
    sudo apt update
    sudo apt install -y python3-pip
fi
pip install python-dotenv
pip install django
pip install django-cors-headers
pip install bs4
pip install django-request
pip install openai==0.28
pip install google
pip install transformers
pip install torch
pip install accelerate
pip install tensorflow
pip install faiss-cpu
pip install selenium
pip install webdriver-manager

