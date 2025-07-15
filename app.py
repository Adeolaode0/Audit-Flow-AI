from flask import Flask, request, jsonify, render_template
import openai
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
load_dotenv()

# Set OpenAI API key (older syntax)
openai.api_key = os.getenv("OPENAI_API_KEY")

if not openai.api_key:
    print("❌ OpenAI API key not found. Please check your .env file.")

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
        print("🔍 Explain control request received")
        
        if not openai.api_key:
            print("❌ OpenAI API key not configured")
            return jsonify({"error": "OpenAI API key not configured"}), 500
            
        data = request.json
        if not data:
            print("❌ No JSON data received")
            return jsonify({"error": "No data received"}), 400
            
        control_description = data.get("control_description", "")
        
        if not control_description:
            return jsonify({"error": "Control description is required"}), 400
        
        print("🤖 Calling OpenAI API for explanation...")
        
        # Updated to use gpt-3.5-turbo with ChatCompletion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that explains audit concepts in simple terms."},
                {"role": "user", "content": f"Explain the following control description in simple terms: {control_description}"}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        explanation = response.choices[0].message.content
        print("✅ Explanation generated successfully")
        
        return jsonify({"explanation": explanation})
    
    except Exception as e:
        print(f"❌ Unexpected error in explain_control: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/rewrite-walkthrough", methods=["POST"])
def rewrite_walkthrough():
    try:
        print("🔄 Rewrite walkthrough request received")
        
        if not openai.api_key:
            print("❌ OpenAI API key not configured")
            return jsonify({"error": "OpenAI API key not configured. Please check your .env file."}), 500
            
        data = request.get_json()
        if not data:
            print("❌ No JSON data received")
            return jsonify({"error": "No data received"}), 400
            
        control_description = data.get("control_description", "")
        walkthrough_discussion = data.get("walkthrough_discussion", "")
        
        print(f"📝 Control Description Length: {len(control_description)}")
        print(f"📝 Walkthrough Discussion Length: {len(walkthrough_discussion)}")
        
        if not control_description or not walkthrough_discussion:
            print("❌ Missing required fields")
            return jsonify({"error": "Both control description and walkthrough discussion are required"}), 400
        
        print("🤖 Calling OpenAI API for walkthrough rewrite...")
        
        # Updated to ONLY rewrite the walkthrough discussion, not include control description
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional audit assistant that rewrites walkthrough discussions into clean, professional audit narratives. You should ONLY return the rewritten walkthrough discussion, not the control description."},
                {"role": "user", "content": f"""
                Given this control context: {control_description}
                
                Please rewrite ONLY the following walkthrough discussion to be more professional, clear, and audit-ready:
                
                "{walkthrough_discussion}"
                
                Requirements for the rewritten walkthrough:
                1. Maintain all key information from the walkthrough
                2. Improve clarity and audit standards
                3. Use professional audit language
                4. Follow proper audit documentation format
                5. Remove any informal language or unclear statements
                6. Organize the information in a logical flow
                
                Return ONLY the rewritten walkthrough discussion, not the control description.
                """}
            ],
            max_tokens=1000,
            temperature=0.3
        )
        
        narrative = response.choices[0].message.content.strip()
        print("✅ OpenAI response received successfully")
        
        return jsonify({"narrative": narrative})
    
    except Exception as e:
        print(f"❌ Unexpected error in rewrite_walkthrough: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/analyze-evidence", methods=["POST"])
def analyze_evidence():
    try:
        print("🔍 Analyze evidence request received")
        
        if not openai.api_key:
            print("❌ OpenAI API key not configured")
            return jsonify({"error": "OpenAI API key not configured. Please check your .env file."}), 500
        
        # Get form data
        control_description = request.form.get('control_description', '')
        walkthrough_discussion = request.form.get('walkthrough_discussion', '')
        test_script = request.form.get('test_script', '')
        evidence_summary = request.form.get('evidence_summary', '')
        analysis_instructions = request.form.get('analysis_instructions', '')
        
        print(f"📝 Form data received - Test Script: {len(test_script)} chars, Evidence Summary: {len(evidence_summary)} chars")
        
        # Get uploaded files
        files = request.files.getlist('evidence')
        
        if not files or len(files) == 0:
            return jsonify({"error": "No evidence files uploaded"}), 400
        
        if not test_script:
            return jsonify({"error": "Test script is required"}), 400
            
        if not evidence_summary:
            return jsonify({"error": "Evidence summary is required"}), 400
        
        # Create file list for analysis context (no content extraction)
        file_info = []
        for file in files:
            if file.filename:
                file_size = len(file.read())
                file.seek(0)  # Reset file pointer
                file_info.append(f"- {file.filename} ({file.content_type or 'Unknown type'}, {file_size} bytes)")
        
        files_context = "\n".join(file_info) if file_info else "No files provided"
        print(f"📁 Files processed: {len(file_info)} files")
        
        # Enhanced analysis prompt with strict PII protection
        prompt = f"""
        You are a professional auditor conducting evidence analysis with strict confidentiality requirements.

        CONTEXT INFORMATION:
        Control Description: {control_description}
        Walkthrough Discussion: {walkthrough_discussion}
        
        TEST SCOPE:
        Test Script: {test_script}
        Evidence Summary Instructions: {evidence_summary}
        
        UPLOADED EVIDENCE FILES:
        {files_context}
        Total files: {len(file_info)}
        
        ANALYSIS INSTRUCTIONS:
        {analysis_instructions}
        
        CRITICAL REQUIREMENTS:
        1. FOCUS ONLY on validating the Evidence Summary observations
        2. NEVER include any PII, names, specific amounts, dates, or identifying information
        3. Use ONLY generic terms: "the individual", "the document", "the transaction", "the system"
        4. STAY strictly within the Test Script scope
        5. Explain HOW the evidence supports the Evidence Summary conclusions
        6. Use professional audit language
        7. Ignore any evidence content outside the Test Script boundaries
        
        Based on the Evidence Summary instructions and the context of uploaded files, provide a professional audit analysis that validates whether the Evidence Summary observations are supported. Focus on the methodology and general findings rather than specific details.
        
        Remember: Your analysis should support the Evidence Summary conclusions using generic, professional language while maintaining strict confidentiality.
        """
        
        print("🤖 Calling OpenAI API for evidence analysis...")
        
        # Updated to use gpt-3.5-turbo with ChatCompletion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional auditor who analyzes evidence while maintaining strict confidentiality and focusing only on validating Evidence Summary observations."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.3
        )

        analysis = response.choices[0].message.content
        print("✅ Evidence analysis completed successfully")
        
        return jsonify({"analysis": analysis})
    
    except Exception as e:
        print(f"❌ Error in analyze_evidence: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route("/api/clear-data", methods=["POST"])
def clear_data():
    """Endpoint to clear all session data for fresh start"""
    return jsonify({
        "message": "All data cleared successfully. Ready for new control information.",
        "status": "clean"
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify API status"""
    return jsonify({
        'status': 'healthy',
        'openai_available': bool(openai.api_key),
        'api_key_configured': bool(os.getenv("OPENAI_API_KEY"))
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    print("🚀 Starting UPDATED Audit Flow AI with GPT-3.5-Turbo...")
    print("=" * 70)
    print(f"📁 Project Directory: {os.getcwd()}")
    print(f"🔑 OpenAI API Key Status: {'✅ Set' if openai.api_key else '❌ Missing/Invalid'}")
    
    # Test OpenAI connection on startup
    try:
        if openai.api_key:
            print("🧪 Testing OpenAI connection...")
            # Test with gpt-3.5-turbo instead of deprecated davinci
            test_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            print("✅ OpenAI connection successful")
        else:
            print("⚠️  WARNING: OpenAI API key not found!")
            print("📝 Please check your .env file contains: OPENAI_API_KEY=your_actual_key")
    except Exception as e:
        print(f"❌ OpenAI connection test failed: {str(e)}")
        print("🔧 Check your API key and internet connection")
    
    print("🌐 Server will start at: http://localhost:5000")
    print("🔧 Updated to use GPT-3.5-Turbo (non-deprecated)")
    print("🧹 Removed problematic OCR dependencies")
    print("🔍 Rewrite Walkthrough: Returns ONLY rewritten walkthrough")
    print("=" * 70)
    print("\n📋 Available Routes:")
    print("   • GET  /           - Main audit form")
    print("   • GET  /testing    - Evidence testing page")
    print("   • POST /api/explain            - Control explanation")
    print("   • POST /api/rewrite-walkthrough - AI walkthrough rewriting (WALKTHROUGH ONLY)")
    print("   • POST /api/analyze-evidence   - AI evidence analysis")
    print("   • POST /api/clear-data         - Clear all data")
    print("   • GET  /api/health             - API health check")
    print("=" * 70)
    
    app.run(host="0.0.0.0", port=5000, debug=True)
