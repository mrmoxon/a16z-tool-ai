from fastapi import FastAPI, Request
from app.api.chat import router as chat_router
from fastapi.responses import JSONResponse
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

app = FastAPI()

# Include the router with the correct prefix
app.include_router(chat_router, prefix="/api")

@app.get("/")
async def root():
    logger.info("Received request to root endpoint")
    return {"message": "Welcome to the Chat API"}

@app.get("/health")
async def status():
    logger.info("Received request to health endpoint")
    return {"status": "Healthy"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected error occurred: {str(exc)}"},
    )

# Add this line for debugging
logger.info(f"App routes: {[route.path for route in app.routes]}")

if __name__ == "__main__":
    logger.info("Starting the FastAPI application")
    uvicorn.run(app, host="0.0.0.0", port=8000)