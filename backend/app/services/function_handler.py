from datetime import datetime
import random
import httpx
from app.core.config import settings

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

function_handler = FunctionHandler()