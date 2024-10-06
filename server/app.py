from flask import Flask, send_file
import os

app = Flask(__name__)

SAMPLE_DATA_DIR = os.path.join(os.path.dirname(__file__), "sample_data")

@app.route('/get_sample_data', methods=['GET'])
def get_sample_data():
    try:
        docx_path = os.path.join(SAMPLE_DATA_DIR, "patient_report.docx")
        pdf_path = os.path.join(SAMPLE_DATA_DIR, "patient_report.pdf")
        image_path = os.path.join(SAMPLE_DATA_DIR, "rainfall.jpg")
        text_path = os.path.join(SAMPLE_DATA_DIR, "test.txt")
        
        if not all(os.path.exists(path) for path in [docx_path, pdf_path, image_path]):
            return "One or more sample files are missing", 404
        
        return {
            "docx_file": f"/download/docx",
            "pdf_file": f"/download/pdf",
            "image_file": f"/download/image",
            "text_file": f"/download/txt"
        }
    except Exception as e:
        return str(e), 500

@app.route('/download/<file_type>', methods=['GET'])
def download_file(file_type):
    if file_type == 'docx':
        return send_file(os.path.join(SAMPLE_DATA_DIR, "patient_report.docx"), as_attachment=True)
    elif file_type == 'pdf':
        return send_file(os.path.join(SAMPLE_DATA_DIR, "patient_report.pdf"), as_attachment=True)
    elif file_type == 'image':
        return send_file(os.path.join(SAMPLE_DATA_DIR, "rainfall.jpg"), as_attachment=True)
    elif file_type == 'txt':
        return send_file(os.path.join(SAMPLE_DATA_DIR, "test.txt"), as_attachment=True)
    else:
        return "Invalid file type", 400

if __name__ == '__main__':
    app.run(port=5000)