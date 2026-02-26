# Natiq Arabi - ElevenLabs & OpenAI Edition

This project uses:
1.  **ElevenLabs Scribe API** for high-accuracy Arabic pronunciation practice.
2.  **OpenAI API** for interactive Arabic voice chat.

## Setup Instructions

1.  **Install Python Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Configure API Keys**:
    -   Create a file named `.env` in this folder.
    -   Add your API Keys:
        ```env
        ELEVENLABS_API_KEY=your_elevenlabs_key_here
        OPENAI_API_KEY=your_openai_key_here
        ```

3.  **Run the Backend**:
    ```bash
    uvicorn backend:app --reload
    ```
    The server will start at `http://localhost:8000`.

4.  **Open the Application**:
    -   Open `NatiqArabic.html` in your browser.
    -   **Pronunciation Tab**: Practice specific sentences.
    -   **Voice Chat Tab**: Have a conversation with an AI Arabic teacher!

## Deployment (Render/Replit)

### Render
1.  Create a `requirements.txt` with:
    ```
    fastapi
    uvicorn
    python-multipart
    requests
    python-dotenv
    openai
    ```
2.  Connect your repository to Render
3.  Select "Web Service".
4.  Set Build Command: `pip install -r requirements.txt`
5.  Set Start Command: `uvicorn backend:app --host 0.0.0.0 --port $PORT`
6.  Add Environment Variables in Render dashboard:
    -   `ELEVENLABS_API_KEY`
    -   `OPENAI_API_KEY`

### Replit
1.  Import project.
2.  Add `ELEVENLABS_API_KEY` and `OPENAI_API_KEY` to Secrets (Tools > Secrets).
3.  Run command: `python backend.py`
