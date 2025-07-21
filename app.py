import os
import json
from flask import Flask, render_template, request, jsonify, send_file
from openai import OpenAI  # Updated for OpenAI v1.x
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import PyPDF2
import docx
import tempfile
import io

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Initialize OpenAI client (new style)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Allowed file extensions for evidence upload
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'csv', 'xlsx', 'xls', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file):
    """Extract text content from uploaded files"""
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()
    try:
        if file_ext == 'txt':
            return file.read().decode('utf-8')
        elif file_ext == 'pdf':
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        elif file_ext in ['docx', 'doc']:
            doc_file = docx.Document(file)
            text = ""
            for paragraph in doc_file.paragraphs:
                text += paragraph.text + "\n"
            return text
        else:
            return f"[File: {filename} - Content not extracted for this file type]"
    except Exception as e:
        return f"[Error extracting text from {filename}: {str(e)}]"

@app.route('/')
def index():
    """Main form page"""
    return render_template('index.html')

@app.route('/testing')
def testing():
    """Evidence testing page"""
    return render_template('testing.html')

@app.route('/api/health')
def api_health():
    """Check API health and OpenAI connection"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=10
        )
        return jsonify({
            'status': 'healthy',
            'openai_connected': True,
            'message': 'All systems operational',
            'model': 'gpt-3.5-turbo'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'openai_connected': False,
            'error': str(e)
        }), 500

@app.route('/api/rewrite-walkthrough', methods=['POST'])
def rewrite_walkthrough():
    """Rewrite walkthrough discussion using AI"""
    try:
        data = request.get_json()
        control_description = data.get('control_description', '')
        walkthrough_discussion = data.get('walkthrough_discussion', '')
        if not control_description or not walkthrough_discussion:
            return jsonify({'error': 'Both control description and walkthrough discussion are required'}), 400
        prompt = f"""
You are a professional auditor. Please rewrite the following walkthrough discussion to be more professional, clear, and comprehensive.

Control Context:
{control_description}

Original Walkthrough Discussion:
{walkthrough_discussion}

Please provide a professionally rewritten version that:
1. Uses proper audit terminology
2. Is clear and concise
3. Follows professional audit documentation standards
4. Maintains all important details from the original
5. Improves structure and flow
6. Enhances professional language

Provide only the rewritten walkthrough discussion:
"""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional auditor with expertise in control documentation and audit standards."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        rewritten_narrative = response.choices[0].message.content.strip()
        return jsonify({
            'success': True,
            'narrative': rewritten_narrative
        })
    except Exception as e:
        print(f"❌ Error in rewrite_walkthrough: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analyze-evidence', methods=['POST'])
def analyze_evidence():
    """Analyze uploaded evidence files using AI"""
    try:
        control_objective = request.form.get('control_objective', '')
        risk_statement = request.form.get('risk_statement', '')
        control_description = request.form.get('control_description', '')
        walkthrough_discussion = request.form.get('walkthrough_discussion', '')
        test_script = request.form.get('test_script', '')
        evidence_summary = request.form.get('evidence_summary', '')
        analysis_instructions = request.form.get('analysis_instructions', '')
        files = request.files.getlist('evidence')
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files uploaded'}), 400
        evidence_content = []
        total_content_length = 0
        MAX_TOTAL_CONTENT = 50000  # Limit total content to 50k characters
        for file in files:
            if file and allowed_file(file.filename):
                try:
                    file.seek(0, 2)
                    file_size = file.tell()
                    file.seek(0)
                    if file_size > 10 * 1024 * 1024:
                        evidence_content.append(f"=== {file.filename} ===\nFile too large (>{file_size/1024/1024:.1f}MB). Please use smaller files.\n")
                        continue
                    text_content = extract_text_from_file(file)
                    if len(text_content) > 10000:
                        text_content = text_content[:10000] + "\n[Content truncated due to size...]"
                    file_content = f"=== {file.filename} ===\n{text_content}\n"
                    if total_content_length + len(file_content) > MAX_TOTAL_CONTENT:
                        evidence_content.append(f"=== {file.filename} ===\n[File skipped - total content limit reached]\n")
                        break
                    evidence_content.append(file_content)
                    total_content_length += len(file_content)
                except Exception as e:
                    evidence_content.append(f"=== {file.filename} ===\nError reading file: {str(e)}\n")
        if not evidence_content:
            return jsonify({'error': 'No valid files could be processed'}), 400
        combined_evidence = "\n".join(evidence_content)
        max_prompt_length = 12000
        if len(combined_evidence) > max_prompt_length:
            combined_evidence = combined_evidence[:max_prompt_length] + "\n[Evidence truncated due to length limits...]"
        analysis_prompt = f"""
{analysis_instructions}

AUDIT CONTEXT:
Control Objective: {control_objective[:500]}
Risk Statement: {risk_statement[:500]}
Control Description: {control_description[:1000]}
Walkthrough Discussion: {walkthrough_discussion[:1000]}
Test Script: {test_script[:1000]}
Evidence Summary Instructions: {evidence_summary[:1000]}

EVIDENCE FILES CONTENT:
{combined_evidence}

Please provide a comprehensive audit analysis that validates the Evidence Summary instructions by examining the uploaded evidence. Follow all privacy and scope requirements specified in the instructions above.
"""
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional auditor analyzing evidence files. Follow all privacy protection requirements and scope limitations strictly."},
                {"role": "user", "content": analysis_prompt}
            ],
            max_tokens=2000,
            temperature=0.3
        )
        analysis_result = response.choices[0].message.content.strip()
        return jsonify({
            'success': True,
            'analysis': analysis_result,
            'files_processed': len(evidence_content),
            'total_content_size': total_content_length
        })
    except Exception as e:
        print(f"❌ Error in analyze_evidence: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-data', methods=['POST'])
def clear_data():
    """Clear server-side data (placeholder endpoint)"""
    return jsonify({
        'success': True,
        'message': 'Server data cleared successfully'
    })

if __name__ == '__main__':
    print("🚀 Starting Audit Flow AI with GPT-3.5-Turbo...")
    print("=" * 70)
    print(f"📁 Project Directory: {os.getcwd()}")
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print("🔑 OpenAI API Key Status: ✅ Set")
        try:
            print("🧪 Testing OpenAI connection...")
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5
            )
            print("✅ OpenAI connection successful")
        except Exception as e:
            print(f"❌ OpenAI connection failed: {e}")
    else:
        print("❌ OpenAI API Key Status: Not set")
        print("Please add your OpenAI API key to the .env file")
    print("🌐 Server will start at: http://localhost:5000")
    print("=" * 70)
    app.run(debug=True,
