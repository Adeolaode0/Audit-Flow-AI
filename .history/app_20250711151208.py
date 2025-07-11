from flask import Flask, request, jsonify, render_template
import openai
import os
from dotenv import load_dotenv
from PyPDF2 import PdfReader
from PIL import Image
import pytesseract
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    raise ValueError("OpenAI API key not found. Please check your .env file.")
# Load environment variables
pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"  # Update path if necessary
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/testing")
def testing():
    return render_template("testing.html")

@app.route("/api/explain", methods=["POST"])
def explain_control():
    try:
        data = request.json
        control_description = data.get("control_description", "")
        
        if not control_description:
            return jsonify({"error": "Control description is required"}), 400
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that explains concepts in simple terms."},
                {"role": "user", "content": f"Explain the following control description in a way a 5th grader can understand: {control_description}"}
            ]
        )
        
        explanation = response["choices"][0]["message"]["content"]
        return jsonify({"explanation": explanation})
    
    except openai.error.RateLimitError:
        return jsonify({"error": "You have exceeded your quota. Please check your OpenAI account."}), 429
    except openai.error.AuthenticationError:
        return jsonify({"error": "Invalid API key. Please check your OpenAI account."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/rewrite-walkthrough", methods=["POST"])
def rewrite_walkthrough():
    try:
        data = request.json
        control_description = data.get("control_description", "")
        walkthrough_discussion = data.get("walkthrough_discussion", "")
        
        if not control_description or not walkthrough_discussion:
            return jsonify({"error": "Both control description and walkthrough discussion are required"}), 400
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that rewrites discussions into clean audit narratives."},
                {"role": "user", "content": f"Rewrite the following walkthrough discussion into a clean audit narrative based on this control description:\n\nControl Description: {control_description}\n\nWalkthrough Discussion: {walkthrough_discussion}"}
            ]
        )
        
        narrative = response["choices"][0]["message"]["content"]
        return jsonify({"narrative": narrative})
    
    except openai.error.RateLimitError:
        return jsonify({"error": "You have exceeded your quota. Please check your OpenAI account."}), 429
    except openai.error.AuthenticationError:
        return jsonify({"error": "Invalid API key. Please check your OpenAI account."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI that reviews evidence based on test scripts."},
                {"role": "user", "content": f"Analyze the following evidence to determine if it satisfies the test requirements:\n\n{evidence_content}"}
            ]
        )

        analysis = response["choices"][0]["message"]["content"]
        return jsonify({"analysis": analysis})
    
    except openai.error.RateLimitError:
        return jsonify({"error": "You have exceeded your quota. Please check your OpenAI account."}), 429
    except openai.error.AuthenticationError:
        return jsonify({"error": "Invalid API key. Please check your OpenAI account."}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=True)