
from flask import Flask, request, url_for, render_template_string
from io import BytesIO
from PyPDF2 import PdfReader
from docx import Document
import requests

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>EvaL - Upload RFP</title>
  <style>
    body {
      margin: 0;
      font-family: 'Source Sans Pro', sans-serif;
      background-color: #F6F8FB;
      overflow-x: hidden;
    }

    .eval-header {
      background-color: #4B6076;
      color: white;
      width: 100%;
      height: 130px;
      display: flex;
      align-items: center;
      padding-left: 50px;
      box-sizing: border-box;
      position: fixed;
      top: 0;
      left: 0;
      z-index: 10;
    }

    .logo {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      justify-content: center;
      align-items: center;
      overflow: hidden;
      margin-right: 15px;
    }

    .logo img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .text-group {
      display: flex;
      flex-direction: column;
      justify-content: center;
    }

    .text-group h2 {
      margin: 0;
      font-weight: 700;
      font-size: 26px;
      line-height: 1.1;
    }

    .text-group p {
      margin-top: 3px;
      font-size: 14px;
      color: #D3DAE2;
    }

    .tagline {
      position: absolute;
      bottom: 10px;
      left: 50px;
      font-size: 11px;
      color: #C8D0DA;
      letter-spacing: 2px;
    }

    main {
      margin-top: 200px;
      display: flex;
      justify-content: center;
    }

    .upload-container {
      background-color: #E9EDF3;
      border-radius: 12px;
      padding: 40px 60px;
      width: 80%;
      max-width: 900px;
      box-sizing: border-box;
    }

    .upload-title {
      font-size: 18px;
      font-weight: 600;
      color: #1E2B37;
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 25px;
    }

    .upload-box {
      background-color: #CFD6E0;
      border: 2px solid #B7C0CC;
      border-radius: 10px;
      text-align: center;
      padding: 60px 20px;
      color: #2B3B4F;
      position: relative;
      transition: border 0.3s ease;
    }

    .upload-box:hover { border-color: #5CC4B4; }

    .upload-box img {
      width: 60px;
      height: 60px;
      margin-bottom: 15px;
    }

    .upload-box p {
      margin: 0;
      font-weight: 600;
      font-size: 16px;
      color: #324055;
    }

    .upload-box small {
      display: block;
      margin-top: 5px;
      margin-bottom: 25px;
      color: #5A687A;
      font-size: 13px;
    }

    .upload-btn {
      background-color: #5CC4B4;
      color: white;
      border: none;
      border-radius: 6px;
      padding: 10px 24px;
      font-weight: 500;
      font-size: 15px;
      cursor: pointer;
      transition: background-color 0.3s ease;
    }

    .upload-btn:hover {
      background-color: #4FB0A2;
    }

    input[type="file"] {
      display: none;
    }

    .output-box {
      background: white;
      border-radius: 8px;
      border: 1.5px solid #D0D6DE;
      margin-top: 30px;
      padding: 20px;
      height: 250px;
      overflow-y: auto;
      color: #1E293B;
      line-height: 1.5;
      white-space: pre-wrap;
    }
  </style>
</head>
<body>
  <header class="eval-header">
    <div class="logo">
      <img src="{{ logo_url }}" alt="EvaL Logo">
    </div>
    <div class="text-group">
      <h2>EvaL</h2>
      <p>AI-Powered RFP Evaluation Platform</p>
    </div>
    <div class="tagline">EXTRACT • VALIDATE • ANALYZE • LEARN</div>
  </header>

  <main>
    <div class="upload-container">
      <div class="upload-title">📁 Upload RFP Documents</div>
      <form id="uploadForm" method="POST" enctype="multipart/form-data">
        <div class="upload-box">
          <img src="https://cdn-icons-png.flaticon.com/512/1091/1091936.png" alt="upload icon">
          <p>Drop your RFP</p>
          <small>Support for PDF, DOCX</small>

          <input id="fileInput" type="file" name="file" accept=".pdf,.docx" required>
          <button type="button" class="upload-btn" id="selectBtn">Select File</button>
        </div>
      </form>

      {% if text %}
      <div class="output-box">{{ text }}</div>
      {% endif %}
    </div>
  </main>

  <script>
    const selectBtn = document.getElementById('selectBtn');
    const fileInput = document.getElementById('fileInput');
    const form = document.getElementById('uploadForm');

    selectBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
      if (fileInput.files.length > 0) form.submit();
    });
  </script>
</body>
</html>
"""

BACKEND_URL = "http://127.0.0.1:8000/upload_file"

@app.route("/", methods=["GET", "POST"])
def index():
    text_output = ""
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            try:
                response = requests.post(
                    BACKEND_URL,
                    files={"file": (file.filename, file.stream, file.content_type)}
                )
                data = response.json()
                if "error" in data:
                    text_output = f"Backend Error: {data['error']}"
                else:
                    text_output = data.get("cleaned_text", "No text returned.")
            except Exception as e:
                text_output = f"Request failed: {e}"

    logo_url = url_for("static", filename="logoH.png")
    return render_template_string(HTML_PAGE, logo_url=logo_url, text=text_output)


if __name__ == "__main__":
    app.run(port=5000, debug=True)
