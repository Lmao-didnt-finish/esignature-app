# 🎈 Blank app template

A simple Streamlit app template for you to modify!

[![Open in Streamlit](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://blank-app-template.streamlit.app/)

### How to run it on your own machine

1. Install the requirements

   ```
   $ pip install -r requirements.txt
   ```

2. Run the app

   ```
   $ streamlit run streamlit_app.py
   ```

Simple Streamlit app to watermark images with an e-signature.

Run:

```bash
$ cd /workspaces/esignature-app
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501 --server.enableCORS false
```

Open on the host: "$BROWSER" http://localhost:8501
