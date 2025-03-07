import os
import time
import random
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

def call_llm(prompt: str, json_mode: bool = False, max_retries: int = 3, initial_backoff: float = 1.0) -> str:
    """
    OpenAI LLMへのAPI呼び出しを行い、応答を返す。失敗した場合は自動的にリトライする。
    
    Args:
        prompt (str): LLMに送信するプロンプト
        json_mode (bool): JSONモードを有効にするかどうか（デフォルト: False）
        max_retries (int): 最大リトライ回数（デフォルト: 3）
        initial_backoff (float): 初期バックオフ時間（秒）（デフォルト: 1.0）
        
    Returns:
        str: LLMからの応答テキスト
    """
    # Initialize the OpenAI LLM with appropriate parameters
    llm_params = {
        "model": "gpt-4o",  # or another appropriate model
        "temperature": 0.7,
        "model_kwargs": {}  # 追加：model_kwargsディクショナリを初期化
    }
    
    # Add JSON mode if requested
    if json_mode:
        llm_params["model_kwargs"]["response_format"] = {"type": "json_object"}
    
    # Initialize the OpenAI LLM
    llm = ChatOpenAI(**llm_params)
    
    # Create a message with the prompt
    message = HumanMessage(content=prompt)
    
    retries = 0
    while True:
        try:
            # Get the response from the LLM
            response = llm.invoke([message])
            
            # Return the content of the response as a string
            return str(response.content)
            
        except Exception as e:
            retries += 1
            if retries > max_retries:
                print(f"Failed after {max_retries} attempts. Last error: {e}")
                return f"Error: リトライ ({max_retries}回) 後も失敗しました: {str(e)}"
            
            # Calculate backoff time with jitter to avoid thundering herd problem
            backoff_time = initial_backoff * (2 ** (retries - 1)) * (0.5 + random.random())
            print(f"Attempt {retries} failed with error: {e}. Retrying in {backoff_time:.2f} seconds...")
            time.sleep(backoff_time) 
