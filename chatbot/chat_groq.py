######################################################################################################################
######################################################################################################################

import json
from groq import Client  
import logging
import os
from dotenv import load_dotenv
from config.config_file import LOGS_DIR 
from chatbot.process import start_process , hybrid_search
from prompts.prompt import SYSTEM_PROMPT_TEMPLATE

######################################################################################################################
######################################################################################################################

load_dotenv()

######################################################################################################################
######################################################################################################################

logger = logging.getLogger(__name__)

######################################################################################################################
######################################################################################################################

def chat_llm(question,knowledge):
    logger.info(f"Starting the LLM processing")
    # 🔑 Replace with your actual API key
    API_KEY = os.getenv("API_KEY")
    

    logger.info(f"Knowledge :: {knowledge}")
    # Convert JSON knowledge into a string context
    if isinstance(knowledge, dict):
        context_data = json.dumps(knowledge, indent=2)
    elif isinstance(knowledge, list):
        context_data = "\n".join([json.dumps(item) for item in knowledge])
    else:
        context_data = str(knowledge)

    # Initialize Groq client
    client = Client(api_key=API_KEY)

    # System + context prompt
    system_prompt =system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context_data=context_data)


    # Send request to Groq API
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-maverick-17b-128e-instruct",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        temperature=0.7,
        max_completion_tokens=1024,
        top_p=1,
        stream=True,
        stop=None
    )

    # Collect streamed response
    response = ""
    for chunk in completion:
        response += chunk.choices[0].delta.content or ""

    return response

######################################################################################################################
######################################################################################################################