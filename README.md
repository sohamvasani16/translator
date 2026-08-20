# PDF Layout & Table Preserving Translator Web Application

A full-stack, production-ready Python web application for translating PDF documents into **Hindi, Gujarati, Spanish, French, German, Japanese, Chinese, Arabic**, and 20+ languages while preserving exact bounding box coordinates `(x0, y0, x1, y1)`, page layouts, images, and tables.

---

## 🌟 Key Features

1. **Exact Layout & Table Preservation**:
   - Uses **PyMuPDF (`pymupdf`)** to extract text blocks along with exact bounding box coordinates.
   - Selective text redaction (`fitz.PDF_REDACT_IMAGE_NONE`) clears original text while preserving table borders, graphics, and background images.

2. **Auto-Scaling Font Size**:
   - Calculates font fitting dynamically so translated text never spills outside the original box boundaries.

3. **Multi-Script Unicode Support**:
   - Dynamic **Font Manager** fetches Google **Noto Sans TTF fonts** on-demand for non-Latin scripts (Devanagari for Hindi/Marathi/Nepali, Gujarati, Arabic, Bengali, Tamil, Telugu, CJK for Japanese/Chinese).

4. **Modern UI & Real-Time Progress**:
   - Built with **FastAPI**, **Tailwind CSS**, glassmorphism aesthetics, and responsive layout.
   - Interactive **Drag-and-Drop Dropzone** with instant PDF preview and file size validation.
   - **Real-Time Progress Bar** tracking page-by-page translation status.
   - Direct PDF download button.
   - Monetization **Display Ad Slots** & interactive **FAQ Accordion**.

---

## 🚀 Step-by-Step Setup & Running Guide

### 1. Requirements & Prerequisites
- Python 3.9+
- Internet connection (for initial translation API calls and Noto font downloads)

### 2. Installation

Clone or open the project folder:
```bash
cd "d:/New folder"
```

Install Python dependencies:
```bash
pip install -r requirements.txt
```

### 3. Running the Web Application Locally

Run using FastAPI / Uvicorn:
```bash
python app.py
```
Or directly with Uvicorn CLI:
```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📁 Project Architecture

```
├── app.py                      # FastAPI web server, REST API endpoints, background translation runner
├── translator_engine.py        # PyMuPDF text block extraction, redaction, autoscaling & re-insertion
├── font_manager.py             # Unicode Noto Font fetcher & manager for multi-script PDF rendering
├── translation_service.py      # Deep-translator service wrapper with phrase caching & retries
├── static/
│   ├── css/
│   │   └── custom.css          # Custom styling, animations & ad layout rules
│   └── js/
│       └── app.js              # Drag-drop uploader, progress polling & download handlers
├── templates/
│   └── index.html              # Responsive single-page UI (Tailwind CSS, Lucide icons, Ads, FAQ)
├── requirements.txt            # Python package dependencies
└── README.md                   # Setup and production deployment guide
```

---

## 🛠️ API Reference

### 1. Upload & Translate PDF
- **Endpoint**: `POST /api/translate`
- **Body**: `multipart/form-data`
  - `file`: PDF Document File
  - `target_lang`: Language Code (e.g. `hi`, `gu`, `es`, `fr`, `de`, `ja`, `zh-CN`, `ar`)
- **Response**: `{"job_id": "...", "status": "processing"}`

### 2. Check Translation Progress
- **Endpoint**: `GET /api/progress/{job_id}`
- **Response**:
```json
{
  "status": "completed",
  "progress": 100,
  "current_page": 5,
  "total_pages": 5,
  "message": "Translation completed successfully!"
}
```

### 3. Download Translated PDF
- **Endpoint**: `GET /api/download/{job_id}`
- **Response**: `application/pdf` file download.

---

## 🐳 Production Deployment Guide

### Deploying with Docker

1. Create a `Dockerfile` in the project root:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Build and run the Docker container:
```bash
docker build -t pdf-translator .
docker run -d -p 8000:8000 --name pdf-translator-app pdf-translator
```

### Deploying on Render / Hugging Face Spaces / VPS
- Set build command: `pip install -r requirements.txt`
- Set start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
