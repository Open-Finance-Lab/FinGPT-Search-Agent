import json
import os
import csv
import random  # Import 'random' for 'randint'
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from datascraper import datascraper as ds
from django.shortcuts import render
from django.http import HttpResponse

# from transformers import AutoTokenizer, AutoModelForCausalLM

message_list = [
    {"role": "user",
     "content": "You are a helpful financial assistant. Always answer questions to the best of your ability."}
]



# View to return a random number as JSON
def Get_A_Number(request):
    int_response = random.randint(0, 99)
    return JsonResponse({'resp': int_response})


# Function to call the locally run Gemma 2B model
# def call_local_gemma_model(question):
#     model_path = os.path.join(os.path.dirname(__file__), 'gemma-2-2b-it')
#
#     # Load tokenizer and model for Gemma
#     tokenizer = AutoTokenizer.from_pretrained(model_path)
#     model = AutoModelForCausalLM.from_pretrained(
#         model_path,
#         device_map="auto"
#     )
#
#     # Tokenize and send the question to the model
#     input_ids = tokenizer(question, return_tensors="pt").to("cuda")  # Use CUDA
#     outputs = model.generate(**input_ids, max_length=200)
#
#     # Decode the response
#     response = tokenizer.decode(outputs[0], skip_special_tokens=True)
#
#     return response


# View to handle appending the text from FRONT-END SCRAPER to the message list
@csrf_exempt
def add_webtext(request):
    if request.method == 'POST':
        try:
            body_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        text_content = body_data.get('textContent', '')
        current_url = body_data.get('currentUrl', '')

        # Basic validation
        if not text_content:
            return JsonResponse({"error": "No textContent provided."}, status=400)

        # Stored in USER role as o1-preview does not support system messages
        message_list.append({
            "role": "user",
            "content": text_content
        })

        # Debug prints
        print("[DEBUG] current_url:", current_url)
        print("[DEBUG] message_list updated:", message_list)

        return JsonResponse({"resp": "Text added successfully as user message"})
    else:
        # Graceful error handling
        return JsonResponse({'error': 'Invalid request method; use POST.'}, status=405)

# Ask button
def chat_response(request):
    question = request.GET.get('question', '')
    selected_models = request.GET.get('models', 'o1-preview,gpt-4o')
    models = selected_models.split(',')
    use_rag = request.GET.get('use_rag', 'false').lower() == 'true'

    responses = {}

    for model in models:
        if use_rag:
            # Use the RAG pipeline
            responses[model] = ds.create_rag_response(question, message_list.copy(), model)
        else:
            # Use regular response
            responses[model] = ds.create_response(question, message_list.copy(), model)

    # for model in models:
    #     if model == "gemma-2b":
    #         # Use the locally run Gemma 2B model
    #         responses[model] = ds.create_gemma_response(question, message_list.copy())
    #     else:
    #         # Use GPT-4o or other OpenAI models
    #         responses[model] = ds.create_response(question, message_list.copy(), model)

    return JsonResponse({'resp': responses})


# Advanced Ask Button
@csrf_exempt
def adv_response(request):
    question = request.GET.get('question', '')
    selected_models = request.GET.get('models', 'o1-preview,gpt-4o')
    models = selected_models.split(',')
    use_rag = request.GET.get('use_rag', 'false').lower() == 'true'

    responses = {}

    for model in models:
        if use_rag:
            # Use the RAG pipeline for advanced response
            responses[model] = ds.create_rag_advanced_response(question, message_list.copy(), model)
        else:
            # Use regular advanced response
            responses[model] = ds.create_advanced_response(question, message_list.copy(), model)

    # for model in models:
    #     if model == "gemma-2b":
    #         # Use the locally run Gemma 2B model for advanced response
    #         responses[model] = ds.create_gemma_advanced_response(question, message_list.copy())
    #     else:
    #         # Use GPT-4o or other OpenAI models for advanced response
    #         responses[model] = ds.create_advanced_response(question, message_list.copy(), model)

    return JsonResponse({'resp': responses})


# # View to handle chat responses
# def chat_response(request):
#     # Assuming 'create_response' returns a string
#     question = request.GET.get('question', '')
#     print("question is: ", question)
#     #message_list.append( {"role": "user", "content": question})
#     #print(request.body)
#     message_response = ds.create_response(question, message_list)
#     print(message_list)
#     return JsonResponse({'resp': message_response})


@csrf_exempt
def clear(request):
    print("initial message_list = " + str(message_list))
    message_list.clear()

    return JsonResponse({'resp': 'Cleared message list sucessfully' + str(message_list)})  # Return a JsonResponse


@csrf_exempt
def get_sources(request):
    query = request.GET.get('query', '')
    query = str(query)
    print(type(query))
    print("views query is ", query)
    sources = ds.get_sources(query)

    return JsonResponse({'resp': sources})  # Return a JsonResponse


@csrf_exempt
def get_logo(request):
    url = request.Get.get('url', '')

    logo_src = ds.get_website_icon(url)
    return JsonResponse({'resp', logo_src})


# log questions
def log_question(request):
    question = request.GET.get('question', '')
    button_clicked = request.GET.get('button', '')
    current_url = request.GET.get('current_url', '')

    # tmp PATH
    log_path = os.path.join(os.path.dirname(__file__), 'questionLog.csv')

    file_exists = os.path.isfile(log_path)

    if question and button_clicked and current_url:
        # Check if the same question has already been asked on the same URL
        question_exists = False
        if os.path.exists(log_path):
            with open(log_path, 'r') as file:
                reader = csv.reader(file)
                for row in reader:
                    if row[1] == current_url and row[2] == question:
                        question_exists = True
                        break

        if not question_exists:
            with open(log_path, 'a', newline='') as log_file:
                writer = csv.writer(log_file)
                if not file_exists:
                    writer.writerow(['Button', 'URL', 'Question'])
                writer.writerow([button_clicked, current_url, question])

    return JsonResponse({'status': 'success'})


# File path for storing preferred URLs ONLY TEMPORARY SOLUTION
PREFERRED_URLS_FILE = 'preferred_urls.txt'


def get_preferred_urls(request):
    """
    Retrieve the list of preferred URLs from the file.
    """
    if os.path.exists(PREFERRED_URLS_FILE):
        with open(PREFERRED_URLS_FILE, 'r') as file:
            urls = [line.strip() for line in file.readlines()]
    else:
        urls = []

    return JsonResponse({'urls': urls})


@csrf_exempt
def add_preferred_url(request):
    """
    Add a new preferred URL to the file.
    """
    if request.method == 'POST':
        new_url = request.POST.get('url')
        if new_url:
            with open(PREFERRED_URLS_FILE, 'a') as file:
                file.write(new_url + '\n')
            return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'failed'}, status=400)

# def get_goog_urls(request):

#     search_query = request.GET.get('query', '')

#     list_urls = ds.get_goog_urls(search_query)
#     return JsonResponse({'resp': list_urls})
