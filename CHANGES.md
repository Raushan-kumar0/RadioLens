# Fixes applied to MRIG

1. **Removed hardcoded secrets** (`tcl.py` Google API key, `mail.py` Gmail
   address/app password). Both now come from environment variables loaded
   via `.env` (see `.env.example`). Rotate the old exposed key/password —
   they were committed to the repo and should be considered compromised.

2. **Migrated the chatbot off the deprecated Google PaLM API** to Gemini
   (`langchain-google-genai`), and updated LangChain imports to the current
   `langchain-community` package layout.

3. **Fixed `vectordb.as_retriever(score_threshold=0.7)`** — that kwarg
   doesn't do anything on its own; it now correctly uses
   `search_type="similarity_score_threshold"` with `search_kwargs`.

4. **Fixed `FAISS.load_local(...)`** missing the now-required
   `allow_dangerous_deserialization=True` flag (newer LangChain versions
   raise an error without it).

5. **Fixed a bug in `/result`** in `app.py`: it always passed
   `static/uploads/input.jpg` to `pdfgenerator.generate_pdf`, even when a
   `.png` was uploaded. It now uses whichever file was actually saved.

6. **Chatbot chain is now cached** instead of rebuilt (including reloading
   embeddings and the vector DB) on every single `/get` request.

7. **Auto-creates `static/uploads/` and `static/outputs/`** on startup so
   the app doesn't crash on a fresh clone.

8. **Clear errors instead of a raw TensorFlow traceback** when
   `static/final_cnn_model.h5` is missing (it isn't included in the repo —
   train it via `Custom_Cnn.ipynb` or supply your own).

9. **Added `requirements.txt`** — none existed before.

10. **Added `.env.example`** and updated `.gitignore` to exclude `.env`
    and `venv/`.

## Still needed from you
- A trained `static/final_cnn_model.h5` (not included in the repo).
- A `GOOGLE_API_KEY` for Gemini.
- A Gmail address + App Password for sending report emails (optional —
  the app now degrades gracefully and just logs a message if unset).
