from flask import Flask, request, jsonify, render_template
import openai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/explain", methods=["POST"])
def explain_control():
    try:
        data = request.json
        control_description = data.get("control_description", "")
        
        if not control_description:
            return jsonify({"error": "Control description is required"}), 400
        
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that explains concepts in simple terms."},
                {"role": "user", "content": f"Explain the following control description in a way a 5th grader can understand: {control_description}"}
            ]
        )
        
        explanation = response.choices[0].message["content"]
        return jsonify({"explanation": explanation})
    
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
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that rewrites discussions into clean audit narratives."},
                {"role": "user", "content": f"Rewrite the following walkthrough discussion into a clean audit narrative based on this control description:\n\nControl Description: {control_description}\n\nWalkthrough Discussion: {walkthrough_discussion}"}
            ]
        )
        
        narrative = response.choices[0].message["content"]
        return jsonify({"narrative": narrative})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    print("Starting Flask app...")
    app.run(host="0.0.0.0", port=5000, debug=True)
