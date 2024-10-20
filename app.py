import os
from flask import Flask, render_template, request, send_file, abort, jsonify
import demucs.separate
import threading

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'separated'
ALLOWED_EXTENSIONS = {'mp3', 'wav'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

separation_status = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_join(directory, filename):
    """Safely join `directory` and `filename`."""
    filename = os.path.normpath(filename)
    joined_path = os.path.join(directory, filename)
    abs_joined_path = os.path.abspath(joined_path)
    abs_directory = os.path.abspath(directory)
    if not abs_joined_path.startswith(abs_directory):
        return None
    return abs_joined_path

def separate_audio(filename):
    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    output_path = os.path.join(app.config['OUTPUT_FOLDER'], os.path.splitext(filename)[0])
    
    separation_status[filename] = 'processing'
    
    demucs.separate.main(["-n", "htdemucs", "--out", output_path, input_path])
    
    separation_status[filename] = 'complete'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"error": "No file part"})
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No selected file"})
        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)
            
            # Start separation in a separate thread
            threading.Thread(target=separate_audio, args=(file.filename,)).start()
            
            return jsonify({"message": "File uploaded and separation started", "filename": file.filename})
    return render_template('index.html')

@app.route('/status/<filename>')
def get_status(filename):
    status = separation_status.get(filename, 'not_found')
    return jsonify({"status": status})

@app.route('/results/<filename>')
def get_results(filename):
    separated_path = os.path.join(app.config['OUTPUT_FOLDER'], os.path.splitext(filename)[0], 'htdemucs', os.path.splitext(filename)[0])
    if os.path.exists(separated_path):
        separated_files = os.listdir(separated_path)
        return jsonify({"files": separated_files})
    return jsonify({"error": "Separation not complete"})

@app.route('/download/<path:filename>')
def download_file(filename):
    file_path = safe_join(app.config['OUTPUT_FOLDER'], filename)
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        abort(404)

if __name__ == '__main__':
    app.run(debug=True)