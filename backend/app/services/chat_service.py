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
                function_call_name = None
                function_call_arguments = ""
                async for chunk in self.stream_chat_completion(client, messages):
                    if chunk['type'] == 'content':
                        yield json.dumps({"type": "content", "content": chunk['data']}) + "\n"
                        full_response += chunk['data']
                    elif chunk['type'] == 'function_call':
                        if 'name' in chunk['data']:
                            function_call_name = chunk['data']['name']
                            yield json.dumps({"type": "function_call", "function": function_call_name}) + "\n"
                        if 'arguments' in chunk['data']:
                            function_call_arguments += chunk['data']['arguments']

                logger.info(f"Initial response: {full_response}")

                if function_call_name:
                    logger.info(f"Function call detected: {function_call_name}")
                    logger.info(f"Function arguments: {function_call_arguments}")
                    try:
                        # Ensure we have a complete JSON object for arguments
                        while not function_call_arguments.strip().endswith('}'):
                            async for chunk in self.stream_chat_completion(client, messages):
                                if chunk['type'] == 'function_call' and 'arguments' in chunk['data']:
                                    function_call_arguments += chunk['data']['arguments']
                                    if function_call_arguments.strip().endswith('}'):
                                        break

                        function_args = json.loads(function_call_arguments)
                        function_response = await function_handler.call_function(function_call_name, **function_args)
                        logger.info(f"Function response: {function_response}")
                        
                        yield json.dumps({"type": "function_response", "content": function_response}) + "\n"
                        
                        messages.append({
                            "role": "function",
                            "name": function_call_name,
                            "content": function_response
                        })
                        
                        logger.info("Making second call to OpenAI API")
                        async for chunk in self.stream_chat_completion(client, messages):
                            if chunk['type'] == 'content':
                                yield json.dumps({"type": "content", "content": chunk['data']}) + "\n"
                                full_response += chunk['data']
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing function arguments: {str(e)}")
                        error_message = f"Error parsing function arguments: {str(e)}"
                        yield json.dumps({"type": "error", "content": error_message}) + "\n"
                    except Exception as e:
                        logger.error(f"Error calling function: {str(e)}")
                        error_message = f"Error calling function: {str(e)}"
                        yield json.dumps({"type": "error", "content": error_message}) + "\n"

                if conversation_id:
                    self.conversations[conversation_id].append({"role": "assistant", "content": full_response})
                
                logger.info(f"Generated response: {full_response}")

        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            yield json.dumps({"type": "error", "content": str(e)}) + "\n"

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

                            if "content" in delta and delta["content"] is not None:
                                yield {"type": "content", "data": delta["content"]}

                            if "function_call" in delta:
                                yield {"type": "function_call", "data": delta["function_call"]}
                    except json.JSONDecodeError:
                        logger.error(f"Error decoding chunk: {line}")

chat_service = ChatService()