import os
import base64
from mistralai import Mistral
from dotenv import load_dotenv
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import fitz  # PyMuPDF

# Load the .env file
load_dotenv()
api_key = os.getenv("API_KEY")

# Initialize the Mistral client
model = "pixtral-12b-2409"
client = Mistral(api_key=api_key)

# Function to encode image as base64
def encode_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def extract_images_from_pdf(pdf_path):
    images = []
    pdf_document = fitz.open(pdf_path)
    
    for page_num in range(len(pdf_document)):
        page = pdf_document.load_page(page_num)  # Load each page
        pix = page.get_pixmap()  # Get page image as Pixmap
        page_image_path = f"page_{page_num}.jpeg"
        pix.save(page_image_path)  # Save the image
        images.append(encode_image_base64(page_image_path))
    
    return images

# Main function to process inputs and return text output
def process_input(text=None, image_paths=None, pdf_path=None):
    content = []

    # Add text content if provided
    if text:
        content.append({
            "type": "text",
            "text": text
        })

    # Add images from file paths if provided
    if image_paths:
        for image_path in image_paths:
            encoded_image = encode_image_base64(image_path)
            content.append({
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{encoded_image}"
            })

    # Process PDF to extract images
    if pdf_path:
        pdf_images = extract_images_from_pdf(pdf_path)
        for encoded_image in pdf_images:
            content.append({
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{encoded_image}"
            })

    # Make the API request to Mistral's Pixtral model
    chat_response = client.chat.complete(
        model=model,
        messages=[{
            "role": "user",
            "content": content
        }]
    )

    # Return the response from the model
    return chat_response.choices[0].message.content

# Example usage
response = process_input(
    text="Analyze this PDF paying attention to the charts and graphsand image",
    image_paths=["rainfall.jpg"],
    pdf_path="patient_report.pdf"
)
print(response)
