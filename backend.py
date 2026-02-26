import os
import io
import base64
import re
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import difflib

# Load environment variables
load_dotenv()

app = FastAPI(title="Natiq Arabi Backend")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ELEVENLABS_API_KEY = os.getenv("eleven_labs")
if ELEVENLABS_API_KEY:
    ELEVENLABS_API_KEY = ELEVENLABS_API_KEY.strip().strip('"').strip("'")
SCRIBE_URL = "https://api.elevenlabs.io/v1/speech-to-text"

# OpenAI Client Configuration
from openai import OpenAI
import traceback

OPENAI_API_KEY = os.getenv("open_ai") # Try .env key name first

openai_client = None

if OPENAI_API_KEY:
    # Clean up key if it has quotes or spaces
    OPENAI_API_KEY = OPENAI_API_KEY.strip().strip('"').strip("'")
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

class AttemptRequest(BaseModel):
    text: str
    audio: str  # Base64 encoded audio

class AttemptResponse(BaseModel):
    transcript: str
    score: int
    match: bool
    feedback: str

def normalize_arabic(text: str) -> str:
    if not text:
        return ""
    # Remove diacritics (Tashkeel)
    text = re.sub(r'[\u064B-\u065F\u0640]', '', text)
    # Normalize Alef variations
    text = re.sub(r'[أإآ]', 'ا', text)
    # Normalize Teh Marbuta
    text = re.sub(r'ة', 'h', text)
    # Normalize Yeh
    text = re.sub(r'ى', 'y', text)
    return text.strip()

@app.post("/attempt")
async def process_attempt(attempt: AttemptRequest):
    # Check API Key
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ElevenLabs API Key not configured")

    try:
        # Decode base64 audio
        # Handle data URL prefix if present
        if "," in attempt.audio:
            audio_data = base64.b64decode(attempt.audio.split(",")[1])
        else:
            audio_data = base64.b64decode(attempt.audio)
            
        # Prepare request to ElevenLabs
        files = {
            'file': ('audio.wav', audio_data, 'audio/wav')
        }
        data = {
            'model_id': 'scribe_v1',
            # 'language_code': 'ar', # ElevenLabs API usually takes 'language_code'. User specified 'language': 'ar'.
            # I will assume standard Scribe API usage.
            'language_code': 'ar',
            'diarize': 'false', 
        }

        headers = {
            'xi-api-key': ELEVENLABS_API_KEY
        }

        try:
            response = requests.post("https://api.elevenlabs.io/v1/speech-to-text", headers=headers, files=files, data=data)
            response.raise_for_status()
            result = response.json()
            transcript = result.get('text', '')
        except requests.exceptions.RequestException as e:
            print(f"ElevenLabs API Error: {e}")
            if response is not None:
                 print(f"Response content: {response.text}")
            raise HTTPException(status_code=500, detail=f"ElevenLabs API Error: {str(e)}")

        # Calculate score
        normalized_ref = normalize_arabic(attempt.text)
        normalized_trans = normalize_arabic(transcript)
        
        matcher = difflib.SequenceMatcher(None, normalized_ref, normalized_trans)
        similarity = matcher.ratio()
        score = int(similarity * 100)
        
        match = score >= 85

        feedback = "Perfect!" if score >= 90 else "Good try!" if score >= 60 else "Try again"

        return {
            "transcript": transcript,
            "score": score,
            "match": match,
            "feedback": feedback
        }

    except Exception as e:
        print(f"Error processing attempt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/exercise")
async def get_exercise():
    # Return a random exercise (Mock for now as per instructions to just include it)
    return {
        "id": "ex_1",
        "text": "مرحبا بالعالم",
        "reference_audio_url": None # Frontend handles TTS
    }

class VoiceChatRequest(BaseModel):
    audio: str

@app.post("/voice-chat")
async def process_voice_chat(chat_req: VoiceChatRequest):
    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API Key not configured")

    try:
        # 1. Save audio to temporary file
        if "," in chat_req.audio:
            audio_data = base64.b64decode(chat_req.audio.split(",")[1])
        else:
            audio_data = base64.b64decode(chat_req.audio)
        
        # Use specific temp filename to work on Windows
        temp_filename = "temp_voice_chat.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_data)

        try:
            # 2. Transcribe (Whisper) with improved accuracy
            with open(temp_filename, "rb") as audio_file:
                transcript_response = openai_client.audio.transcriptions.create(
                    model="gpt-4o-transcribe", # pervous "whisper-1"
                    file=audio_file,
                    language="ar",
                    prompt="Arabic language learning conversation. Common phrases: مرحبا، شكرا، كيف حالك، أنا بخير"  # Helps with context
                )
            user_text = transcript_response.text

            # 3. Chat Completion (GPT-4o-mini)
            system_prompt = """
                            You are a professional Arabic teacher helping a beginner student practice Arabic conversation.

                            GOALS:
                            - Help the student practice Modern Standard Arabic (MSA)
                            - Keep Arabic sentences simple and beginner-friendly
                            - Encourage speaking and conversation
                            - Gently correct grammar, vocabulary, and pronunciation mistakes

                            LANGUAGE RULES:
                            - Always respond in Arabic first.
                            - After the Arabic section, provide explanations ONLY in English.
                            - Do NOT mix English inside the Arabic sentences.
                            - Keep explanations short and clear.

                            CORRECTION RULES:
                            When the student makes a mistake:
                            1. Repeat their sentence correctly in Arabic.
                            2. Briefly explain the mistake in English.
                            3. Give one more correct example sentence.
                            4. Ask a follow-up question in Arabic to continue practice.

                            PRONUNCIATION RULES:
                            If pronunciation errors are detected:
                            - Write the correct word in Arabic.
                            - Show a simple phonetic hint in English.
                            - Briefly explain the sound difference.

                            FORMAT STRICTLY LIKE THIS:

                            [Arabic Response]

                            (English Explanation:
                            - Correction:
                            - Grammar note:
                            - Pronunciation note (if needed):
                            )

                            If unsure about a grammar explanation, keep the explanation simple.
                            Do not invent complex grammatical terminology.

                            Keep the tone friendly, supportive, and encouraging.
                            """

            chat_response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text}
                ],
                temperature=0.4  # More consistent responses
            )
            ai_text = chat_response.choices[0].message.content

            # 4. Generate Audio (TTS-1-HD) with better voice for multilingual content
            speech_response = openai_client.audio.speech.create(
                model="gpt-4o-mini-tts", # previous "tts-1-hd"
                voice="nova",  # Nova has better pronunciation for Arabic and English mix
                input=ai_text,
                speed=0.9  # Slightly slower for clearer pronunciation
            )
            
            # Convert speech to base64
            # Stream to memory
            audio_io = io.BytesIO()
            for chunk in speech_response.iter_bytes():
                audio_io.write(chunk)
            audio_io.seek(0)
            ai_audio_base64 = base64.b64encode(audio_io.read()).decode('utf-8')

            return {
                "transcript": user_text,
                "response_text": ai_text,
                "response_audio": ai_audio_base64
            }

        finally:
            # Cleanup temp file
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

    except Exception as e:
        print(f"Error processing voice chat: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # Allow running directly
    uvicorn.run(app, host="0.0.0.0", port=8000)


# print("ni hao, peng you")
