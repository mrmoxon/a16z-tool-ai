from datetime import datetime
import random
import httpx
from app.core.config import settings
import json
import os
from PIL import Image
import fitz  # PyMuPDF

class FunctionHandler:
    def __init__(self):
        self.functions = {
            "get_current_time": {
                "function": self.get_current_time,
                "description": "Get the current date and time",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "get_random_number": {
                "function": self.get_random_number,
                "description": "Get a random number between a minimum and maximum value",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "min": {"type": "number", "description": "The minimum value"},
                        "max": {"type": "number", "description": "The maximum value"}
                    },
                    "required": ["min", "max"]
                }
            },
            "brave_search": {
                "function": self.brave_search,
                "description": "Perform a web search for recent information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query"}
                    },
                    "required": ["query"]
                }
            },
            "fetch_portfolio_performance": {
                "function": self.call_endpoint,
                "description": "Call portfolio performance (time series) and process the response",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "query_medical_records": {
                "function": self.query_medical_records,
                "description": "Query the server for the filenames of available medical records",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "download_medical_record": {
                "function": self.download_medical_record,
                "description": "Download a specific medical record from the server",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_type": {"type": "string", "description": "The type of file to download (docx, pdf, image, or txt)"},
                        "session_folder": {"type": "string", "description": "The path to the session folder"}
                    },
                    "required": ["file_type", "session_folder"]
                }
            },
            "assess_file": {
                "function": self.assess_file,
                "description": "Assess the content of a file and provide a summary of its properties and contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "The path to the file to be assessed"},
                        "session_folder": {"type": "string", "description": "The path to the session folder"}
                    },
                    "required": ["file_path", "session_folder"]
                }
            }
        }

    def get_function_descriptions(self):
        return [
            {
                "name": name,
                "description": info["description"],
                "parameters": info["parameters"]
            }
            for name, info in self.functions.items()
        ]

    async def call_function(self, function_name, *args, **kwargs):
        if function_name in self.functions:
            func = self.functions[function_name]["function"]
            # Remove 'session_folder' from kwargs if the function doesn't expect it
            if 'session_folder' in kwargs and 'session_folder' not in func.__code__.co_varnames:
                del kwargs['session_folder']
            result = await func(**kwargs)
            return str(result)  # Convert all results to strings
        else:
            raise ValueError(f"Unknown function: {function_name}")

    @staticmethod
    async def get_current_time():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    async def get_random_number(min: int, max: int):
        return random.randint(min, max)

    @staticmethod
    async def brave_search(query: str):
        print("Performing Brave Search")
        base_url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": settings.BRAVE_API
        }
        params = {
            "q": query
        }

        async with httpx.AsyncClient() as client:
            try:
                print("Sending request to Brave Search API")
                response = await client.get(base_url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return f"Error: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                return f"An error occurred: {str(e)}"

    @staticmethod
    async def call_endpoint():
        headers = {
            "Authorization": f"Bearer eyJraWQiOiJEVHVvM0VOYVZhdldxNk4rVitPV2dvU1Q0Q0tJYlhsTmErb2E4WDhWZTZnPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI2YzI0NzBjNy02Y2E2LTQzYzktYmYzYS0xNThiZDc0ODAxZDEiLCJjb2duaXRvOmdyb3VwcyI6WyJtYW5hZ2VyIl0sImlzcyI6Imh0dHBzOlwvXC9jb2duaXRvLWlkcC5ldS13ZXN0LTIuYW1hem9uYXdzLmNvbVwvZXUtd2VzdC0yX1VNenlka3RjTCIsImNsaWVudF9pZCI6IjcwZnM5czRqNDhtcnB2bmZrMWZ1YmYxYjZrIiwiZXZlbnRfaWQiOiI4MTliNWEyZC0yZGRmLTQyN2QtYTgyMC03ODg5NDcyNGYwNGYiLCJ0b2tlbl91c2UiOiJhY2Nlc3MiLCJzY29wZSI6ImF3cy5jb2duaXRvLnNpZ25pbi51c2VyLmFkbWluIiwiYXV0aF90aW1lIjoxNzI3NDYxMDgyLCJleHAiOjE3MjgyMTA5NTIsImlhdCI6MTcyODIwNzM1MiwianRpIjoiZDRjOTIyY2ItZWM0My00NTQyLWFjYmUtMzNkYjczMWFlMGNiIiwidXNlcm5hbWUiOiI2YzI0NzBjNy02Y2E2LTQzYzktYmYzYS0xNThiZDc0ODAxZDEifQ.EeBekVbG-5L6Hor09drs2nDv8EYpg7qse7qm8Oa8WhKsZXV5ZR7VoObqbbQue0TPV7grQ_mGtDTTF4HOTa9QSmROUyn_H_cFtGsDjXym7kwthYhyS14qipbaVdUNaEWWyNkHBLUQ23ObSmMhAnAZsKWVtbnZHYMvwl5lbW_3VuQp7b1i7rC9C0JlhfNVmN32Hjs3HKyi3WrMnV-xMwkI4Lq74PVdXfsYBF_B57MWntRaNGLgCalRTF35bYEPOmhxHZ33IXF1eB--jNVtcP_9dS_hbEIXCQr4pnFG5dk42D0HnOexybFpcD_SBe5YcGocE-RwDdwYgqXs2zfjuVOClA",
            "Accept": "*/*"
        }

        async with httpx.AsyncClient() as client:
            try:
                url = 'https://stage.illio.com/api/v3/portfolio/9dfc1c38-d96c-4b4b-8e85-7be8ef27fcd0/insight/summary'
                response = await client.get(url, headers=headers)
                response.raise_for_status()

                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    return json.dumps(response.json(), indent=2)
                elif "application/pdf" in content_type:
                    return "PDF content received. Processing of PDF files is not implemented in this example."
                elif "image/png" in content_type:
                    image = Image.open(BytesIO(response.content))
                    return f"PNG image received. Size: {image.size}, Mode: {image.mode}"
                else:
                    return f"Received content of type: {content_type}. Raw content: {response.text[:1000]}..."

            except httpx.HTTPStatusError as e:
                return f"Error: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                return f"An error occurred: {str(e)}"

    @staticmethod
    async def query_medical_records():
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get('http://localhost:5000/get_sample_data')
                response.raise_for_status()
                return json.dumps(response.json(), indent=2)
            except httpx.HTTPStatusError as e:
                return f"Error: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                return f"An error occurred: {str(e)}"

    @staticmethod
    async def download_medical_record(file_type: str, session_folder: str):
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f'http://localhost:5000/download/{file_type}')
                response.raise_for_status()
                
                file_name = f"medical_record.{file_type}"
                file_path = os.path.join(session_folder, file_name)
                
                with open(file_path, 'wb') as f:
                    f.write(response.content)

                return f"File downloaded successfully. Path: {file_path}"
            except httpx.HTTPStatusError as e:
                return f"Error: {e.response.status_code} - {e.response.text}"
            except Exception as e:
                return f"An error occurred: {str(e)}"

    @staticmethod
    async def assess_file(file_path: str, session_folder: str):
        full_path = os.path.join(session_folder, file_path)
        if not os.path.exists(full_path):
            return f"Error: File not found at {full_path}"

        file_size = os.path.getsize(full_path)
        file_ext = os.path.splitext(full_path)[1].lower()

        assessment = f"File: {os.path.basename(full_path)}\n"
        assessment += f"File size: {file_size} bytes\n"
        assessment += f"File type: {file_ext}\n\n"

        if file_ext == '.pdf':
            try:
                with fitz.open(full_path) as doc:
                    assessment += f"PDF file with {len(doc)} pages.\n"
                    toc = doc.get_toc()
                    if toc:
                        assessment += "Table of Contents:\n"
                        for item in toc[:5]:  # Show first 5 ToC items
                            assessment += f"- {' '.join(map(str, item))}\n"
                        if len(toc) > 5:
                            assessment += f"... and {len(toc) - 5} more items\n"
            except Exception as e:
                assessment += f"Unable to analyze PDF structure: {str(e)}\n"

        elif file_ext == '.docx':
            assessment += "DOCX file. Detailed analysis would require additional libraries.\n"

        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
            try:
                with Image.open(full_path) as img:
                    assessment += f"Image file. Dimensions: {img.size[0]}x{img.size[1]} pixels. Mode: {img.mode}.\n"
            except Exception as e:
                assessment += f"Unable to analyze image: {str(e)}\n"

        elif file_ext == '.txt':
            with open(full_path, 'r', encoding='utf-8') as text_file:
                text_content = text_file.read()
            line_count = text_content.count('\n') + 1
            word_count = len(text_content.split())
            assessment += f"Text file containing approximately {line_count} lines and {word_count} words.\n"
            assessment += f"First 100 characters: {text_content[:100]}...\n"

        else:
            assessment += f"This file has an unrecognized file type: {file_ext}\n"

        return assessment

function_handler = FunctionHandler()
