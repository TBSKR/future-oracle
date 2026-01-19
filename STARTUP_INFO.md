# FutureOracle Startup Information

## 🚀 How to Start the Application

### Option 1: Using the startup script (Recommended)
```bash
./start.sh
```

### Option 2: Manual start
```bash
source venv/bin/activate
streamlit run src/app.py --server.port 8501
```

## 📝 Virtual Environment
- Location: `venv/`
- The venv is automatically activated when using `start.sh`
- Install dependencies once with:
  ```bash
  venv/bin/pip install -r requirements.txt
  ```

## 🌐 Access the Application
Open your browser and navigate to:
**http://localhost:8501**

## ⚠️ Note
- Some optional AI dependencies may not be installed/available in every environment. The dashboard will still start; AI-powered pages will show a helpful error until dependencies are installed.
- If `pip install` fails with SSL certificate errors on macOS, ensure your Python has valid certificates (common fix: run the Python “Install Certificates” helper, or configure `SSL_CERT_FILE` via `certifi`).
