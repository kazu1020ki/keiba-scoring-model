import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = PROJECT_ROOT / "reports"

app = FastAPI(title="keiba-scoring-model web API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictRequest(BaseModel):
    race_id: str = Field(pattern=r"^\d{12}$", description="netkeiba race_id 12桁")


class PredictResponse(BaseModel):
    race_id: str
    report_path: str
    report_text: str


def find_latest_report(race_id: str) -> Path | None:
    candidates = sorted(REPORT_DIR.glob(f"report_*_{race_id}.txt"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        return None
    return candidates[-1]


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/predict", response_model=PredictResponse)
def predict(req: PredictRequest):
    cmd = ["python", "run_pipeline_with_report.py", "--race_id", req.race_id]

    try:
        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        detail = (e.stderr or e.stdout or "pipeline failed").strip()
        raise HTTPException(status_code=500, detail=detail)

    report = find_latest_report(req.race_id)
    if not report:
        raise HTTPException(status_code=500, detail="レポート生成に失敗しました")

    return PredictResponse(
        race_id=req.race_id,
        report_path=str(report.relative_to(PROJECT_ROOT)),
        report_text=report.read_text(encoding="utf-8"),
    )
