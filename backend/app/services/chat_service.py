import json
import httpx
import logging
import uuid
import os
import shutil
from fastapi import HTTPException
from app.core.config import settings
from app.models.chat_model import ChatMessage
from app.services.function_handler import function_handler

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.base_folder = "/tmp"
        os.makedirs(self.base_folder, exist_ok=True)
        self.extra_context = """
You are a helpful assistant agent. 

- You can call functions to get additional information when needed. Don't call the same function multiple times in a row.
- When asked to assess medical records, check the records once, then think about how to download them via another function call, and assess them with a third function call.
- All files related to this session are stored in the session folder. You can access this folder path using the 'session_folder' variable.
- Respond in markdown format
"""
        self.conversations = {}
        self.max_turns = 5  # Maximum number of conversation turns

    def create_session_folder(self, conversation_id):
        session_folder = os.path.join(self.base_folder, conversation_id)
        os.makedirs(session_folder, exist_ok=True)
        return session_folder

    def cleanup_session_folder(self, conversation_id):
        session_folder = os.path.join(self.base_folder, conversation_id)
        if os.path.exists(session_folder):
            shutil.rmtree(session_folder)

    async def generate_response(self, chat_message: ChatMessage, conversation_id: str = None):
        try:
            logger.info(f"Generating response for message: {chat_message.message}, conversation_id: {conversation_id}")
            
            if conversation_id is None:
                conversation_id = str(uuid.uuid4())
                session_folder = self.create_session_folder(conversation_id)
                self.conversations[conversation_id] = {
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant who can provide various information, including the current time."},
                        {"role": "system", "content": self.extra_context},
                        {"role": "system", "content": f"The session folder for this conversation is: {session_folder}"}
                    ],
                    "session_folder": session_folder
                }
                logger.info(f"Created new conversation with ID: {conversation_id}")
                yield json.dumps({"type": "conversation_id", "id": conversation_id}) + "\n"
            else:
                if conversation_id not in self.conversations:
                    raise HTTPException(status_code=404, detail="Conversation not found")
                session_folder = self.conversations[conversation_id]["session_folder"]

            self.conversations[conversation_id]["messages"].append({"role": "user", "content": chat_message.message})
            messages = self.conversations[conversation_id]["messages"]

            async with httpx.AsyncClient() as client:
                logger.info(f"Sending request to OpenAI API for conversation ID: {conversation_id}")
                
                full_response = ""
                for turn in range(self.max_turns):
                    function_call_name = None
                    function_call_arguments = ""
                    turn_response = ""

                    async for chunk in self.stream_chat_completion(client, messages):
                        if chunk['type'] == 'content':
                            yield json.dumps({"type": "content", "content": chunk['data']}) + "\n"
                            turn_response += chunk['data']
                        elif chunk['type'] == 'function_call':
                            if 'name' in chunk['data']:
                                function_call_name = chunk['data']['name']
                                yield json.dumps({"type": "function_call", "function": function_call_name}) + "\n"
                            if 'arguments' in chunk['data']:
                                function_call_arguments += chunk['data']['arguments']

                    full_response += turn_response
                    logger.info(f"Turn {turn + 1} response: {turn_response}")

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
                            function_args['session_folder'] = session_folder
                            function_response = await function_handler.call_function(function_call_name, **function_args)
                            logger.info(f"Function response: {function_response}")
                            
                            yield json.dumps({"type": "function_response", "content": function_response}) + "\n"
                            
                            messages.append({
                                "role": "function",
                                "name": function_call_name,
                                "content": function_response
                            })
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing function arguments: {str(e)}")
                            error_message = f"Error parsing function arguments: {str(e)}"
                            yield json.dumps({"type": "error", "content": error_message}) + "\n"
                        except Exception as e:
                            logger.error(f"Error calling function: {str(e)}")
                            error_message = f"Error calling function: {str(e)}"
                            yield json.dumps({"type": "error", "content": error_message}) + "\n"
                    else:
                        # If no function call, break the loop
                        break

                self.conversations[conversation_id]["messages"].append({"role": "assistant", "content": full_response})

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