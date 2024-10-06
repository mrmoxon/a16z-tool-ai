import json
import httpx
import logging
from fastapi import HTTPException
from app.core.config import settings
from app.models.chat_model import ChatMessage
from app.services.function_handler import function_handler

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.extra_context = """
You are a helpful assistant. You can call functions to get additional information when needed.

- Respond in markdown format
"""
        self.conversations = {}

    async def generate_response(self, chat_message: ChatMessage, conversation_id: str = None):
        try:
            logger.info(f"Generating response for message: {chat_message.message}, conversation_id: {conversation_id}")
            
            if conversation_id is None:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant who can provide various information, including the current time."},
                    {"role": "system", "content": self.extra_context},
                    {"role": "user", "content": chat_message.message}
                ]
                logger.info("Using stateless conversation")
            else:
                if conversation_id not in self.conversations:
                    logger.info(f"Creating new conversation history for ID: {conversation_id}")
                    self.conversations[conversation_id] = [
                        {"role": "system", "content": "You are a helpful assistant who can provide various information, including the current time."},
                        {"role": "system", "content": self.extra_context}
                    ]
                self.conversations[conversation_id].append({"role": "user", "content": chat_message.message})
                messages = self.conversations[conversation_id]
                logger.info(f"Using stateful conversation with ID: {conversation_id}")

            async with httpx.AsyncClient() as client:
                logger.info(f"Sending request to OpenAI API for {'stateless chat' if conversation_id is None else f'conversation ID: {conversation_id}'}")
                
                full_response = ""
                function_call = None
                async for chunk in self.stream_chat_completion(client, messages):
                    if chunk['type'] == 'content':
                        yield chunk['data']
                        full_response += chunk['data']
                    elif chunk['type'] == 'function_call':
                        function_call = chunk['data']
                        break  # Stop streaming once we get a function call

                logger.info(f"Initial response: {full_response}")

                if function_call:
                    function_name = function_call.get("name")
                    function_args = function_call.get("arguments", "{}")
                    
                    logger.info(f"Function call detected: {function_name}")
                    logger.info(f"Function arguments: {function_args}")
                    try:
                        # Ensure function_args is a complete JSON object
                        while not function_args.endswith('}'):
                            async for chunk in self.stream_chat_completion(client, messages):
                                if chunk['type'] == 'function_call':
                                    function_args += chunk['data'].get('arguments', '')
                                    if function_args.endswith('}'):
                                        break

                        function_args = json.loads(function_args)
                        function_response = await function_handler.call_function(function_name, **function_args)
                        logger.info(f"Function response: {function_response}")
                        
                        messages.append({
                            "role": "function",
                            "name": function_name,
                            "content": function_response
                        })
                        
                        logger.info("Making second call to OpenAI API")
                        async for chunk in self.stream_chat_completion(client, messages):
                            if chunk['type'] == 'content':
                                yield chunk['data']
                                full_response += chunk['data']
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing function arguments: {str(e)}")
                        error_message = f"\nError parsing function arguments: {str(e)}"
                        yield error_message
                        full_response += error_message
                    except Exception as e:
                        logger.error(f"Error calling function: {str(e)}")
                        error_message = f"\nError calling function: {str(e)}"
                        yield error_message
                        full_response += error_message

                if conversation_id:
                    self.conversations[conversation_id].append({"role": "assistant", "content": full_response})
                
                logger.info(f"Generated response: {full_response}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error decoding JSON: {str(e)}")
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"HTTP error occurred: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

    async def stream_chat_completion(self, client, messages):
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": messages,
                "functions": function_handler.get_function_descriptions(),
                "function_call": "auto",
                "stream": True
            },
            timeout=30.0
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    line = line[6:]  # Remove "data: " prefix
                if line.strip() == "[DONE]":
                    break
                if line:
                    try:
                        chunk_data = json.loads(line)
                        if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                            delta = chunk_data["choices"][0].get("delta", {})

                            if "content" in delta:
                                content = delta["content"]

                                if content is not None:
                                    yield {"type": "content", "data": content}

                            if "function_call" in delta:
                                yield {"type": "function_call", "data": delta["function_call"]}
                    except json.JSONDecodeError:
                        logger.error(f"Error decoding chunk: {line}")

chat_service = ChatService()