# SecondLife – Give E-Waste a New Life
Match unused electronic components to low-voltage reuse projects, with an explainable feasibility score and estimated e-waste reuse.

## Run locally
```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000 (SQLite DB and seed data are created automatically on first start; restarts keep data).

## Demo flow (3-5 min)
Home -> My components -> "Load demo kit" (or add 4-5 parts) -> Find my projects -> open the 100% project -> view matched/missing + estimates -> Impact dashboard.

## Notes
- Score = average of min(available/required, 1) x 100; ranked by score, fully matched parts, then fewest missing.
- Weights/prices are approximate seed estimates, not measurements. No carbon claims.
- Frontend is a single static page (no npm build) served by FastAPI.
