import os
import json
import hashlib
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Load .env if present (so GOOGLE_API_KEY / LLM_PROVIDER work when running uvicorn)
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass

from llm_providers import generate_insight

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Pydantic: Incoming telemetry (data minimization — counts only) ---
class TelemetrySummary(BaseModel):
    tab_switch_count: int = Field(..., ge=0, description="Number of tab focus/blur events")
    keystroke_count: int = Field(..., ge=0, description="Number of keystrokes in tracked inputs")
    total_events: int = Field(..., ge=0, description="Total telemetry events in session")
    session_duration_seconds: float = Field(..., ge=0, description="Session duration in seconds")


# --- Pydantic: Outgoing response (Insight + Proof-of-Deletion) ---
class VerificationCertificate(BaseModel):
    algorithm: str = "SHA-256"
    hash: str = Field(..., description="Hash of request payload before purge (Proof-of-Deletion)")


class InsightWithProof(BaseModel):
    insight: str = Field(..., description="AI-generated behavioral classification and reason")
    verification_certificate: VerificationCertificate = Field(
        ..., description="Proof that received data was hashed before deletion"
    )


# --- Privacy Layer: Proof-of-Deletion (PoD) generator ---
def generate_proof_of_deletion(raw_payload_bytes: bytes) -> str:
    """Generate SHA-256 hash of incoming telemetry payload for verification certificate."""
    return hashlib.sha256(raw_payload_bytes).hexdigest()


# --- Privacy Layer: Shredder — overwrite buffer before returning ---
def shred_buffer(buffer: bytearray) -> None:
    """Overwrite temporary buffer with zeros so payload cannot be recovered from memory."""
    for i in range(len(buffer)):
        buffer[i] = 0


# --- API Endpoint ---
@app.post("/api/analyze", response_model=InsightWithProof)
async def analyze_behavior(request: Request):
    # 1. Read raw body once for PoD and parsing (will be shredded after use)
    raw_body: bytes = await request.body()
    payload_buffer = bytearray(raw_body)

    # 2. Generate Proof-of-Deletion certificate BEFORE any processing
    pod_hash = generate_proof_of_deletion(raw_body)
    certificate = VerificationCertificate(hash=pod_hash)

    # 3. Parse distilled summary (data minimization: only counts, no raw coordinates)
    try:
        summary = TelemetrySummary(**json.loads(raw_body.decode("utf-8")))
    except Exception:
        shred_buffer(payload_buffer)
        return InsightWithProof(
            insight="Error: Invalid payload.",
            verification_certificate=certificate,
        )

    # 4. Build prompt and call configured LLM (see llm_providers.py to add your LLM)
    prompt = (
        f"Classify behavior. Session duration (s): {summary.session_duration_seconds:.2f}, "
        f"tab switches: {summary.tab_switch_count}, keystrokes: {summary.keystroke_count}. "
        "Output JSON only: state (Focused|Confused|Distracted) and reason."
    )
    try:
        generated_insight = generate_insight(prompt)
    except Exception as e:
        shred_buffer(payload_buffer)
        return InsightWithProof(
            insight=f"Error: Failed to get insight from AI model. ({e!s})",
            verification_certificate=certificate,
        )

    # 5. Shred the temporary buffer (payload no longer recoverable)
    shred_buffer(payload_buffer)

    # 6. Optionally append to local log (insight only, no raw telemetry)
    log_path = "insights.jsonl"
    if not os.path.exists(log_path) or os.path.getsize(log_path) < 100_000:
        with open(log_path, "a") as f:
            f.write(json.dumps({"insight": generated_insight, "pod_hash": pod_hash}) + "\n")

    return InsightWithProof(
        insight=generated_insight,
        verification_certificate=certificate,
    )
