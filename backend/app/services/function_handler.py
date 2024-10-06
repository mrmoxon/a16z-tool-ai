from datetime import datetime
import random
import httpx
from app.core.config import settings
import json
from io import BytesIO
from PIL import Image
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import requests
import tempfile
import os
import base64

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
            result = await self.functions[function_name]["function"](**kwargs)
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

function_handler = FunctionHandler()