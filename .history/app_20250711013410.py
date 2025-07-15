from flask import Flask, request, jsonify, render_template
import openai
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract

# Specify the path to Tesseract executable (if needed)
pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"
# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/testing")
def testing():
    return render_template("testing.html")

@app.route("/api/analyze-evidence", methods=["POST"])
def analyze_evidence():
    try:
        # Get the uploaded file
        evidence_file = request.files.get("evidence")
        if not evidence_file:
            return jsonify({"error": "Evidence file is required"}), 400

        # Determine file type and extract text
        evidence_content = None
        if evidence_file.filename.endswith(".pdf"):
            # Extract text from PDF
            try:
                pdf_reader = PdfReader(evidence_file)
                evidence_content = " ".join(page.extract_text() for page in pdf_reader.pages)
            except Exception as e:
                return jsonify({"error": f"Failed to extract text from PDF: {str(e)}"}), 400
        elif evidence_file.filename.lower().endswith((".png", ".jpg", ".jpeg")):
            # Extract text from image
            try:
                image = Image.open(evidence_file)
                evidence_content = pytesseract.image_to_string(image)
            except Exception as e:
                return jsonify({"error": f"Failed to extract text from image: {str(e)}"}), 400
        else:
            return jsonify({"error": "Unsupported file type. Please upload a PDF or image file."}), 400

        if not evidence_content.strip():
            return jsonify({"error": "No text found in the uploaded file."}), 400

        # Use OpenAI to analyze the evidence
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an AI that reviews evidence based on test scripts."},
                {"role": "user", "content": f"Analyze the following evidence to determine if it satisfies the test requirements:\n\n{evidence_content}"}
            ]
        )

        analysis = response["choices"][0]["message"]["content"]
        return jsonify({"analysis": analysis})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=True)