import os
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import db
from engine import recommend, evaluate

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

Condition = Literal["Working", "Partially Working", "Unknown"]
class InvIn(BaseModel):
    component_id: int
    quantity: int = Field(ge=1, le=1000)
    condition: Condition = "Unknown"
class InvUpdate(BaseModel):
    quantity: int = Field(ge=1, le=1000)
    condition: Condition | None = None

app = FastAPI(title="SecondLife API")
db.init()
DEMO_KITS = {
    "default": {"Arduino Uno": 1, "Ultrasonic Sensor": 1, "Servo Motor": 1, "LED": 2, "Buzzer": 1, "Resistor": 3},
    "iot": {"Arduino Uno": 1, "Soil Moisture Sensor": 1, "Relay Module": 1, "DC Motor": 1, "Temperature Sensor": 1, "LCD Display": 1, "Potentiometer": 1},
    "salvaged": {"Raspberry Pi": 1, "Old Webcam": 1, "Old USB Cable": 1, "Old Mobile Charger": 1, "Old Computer Fan": 1, "Old Speaker": 1, "Push Button": 2}
}

def inv_map():
    c = db.conn(); m = {r["component_id"]: r["quantity"] for r in c.execute("SELECT component_id, quantity FROM inventory")}; c.close(); return m

@app.get("/api/components")
def components():
    c = db.conn(); r = [dict(x) for x in c.execute("SELECT * FROM components ORDER BY category, name")]; c.close(); return r

@app.get("/api/inventory")
def inventory():
    c = db.conn()
    r = [dict(x) for x in c.execute("SELECT i.id, i.component_id, i.quantity, i.condition, c.name, c.category, c.estimated_weight_grams FROM inventory i JOIN components c ON c.id=i.component_id ORDER BY c.name")]
    c.close(); return r

@app.post("/api/inventory", status_code=201)
def add_item(item: InvIn):
    c = db.conn()
    if not c.execute("SELECT 1 FROM components WHERE id=?", (item.component_id,)).fetchone():
        raise HTTPException(404, "Unknown component")
    row = c.execute("SELECT id, quantity FROM inventory WHERE component_id=?", (item.component_id,)).fetchone()
    if row: c.execute("UPDATE inventory SET quantity=?, condition=? WHERE id=?", (min(row["quantity"] + item.quantity, 1000), item.condition, row["id"]))
    else: c.execute("INSERT INTO inventory(component_id,quantity,condition) VALUES(?,?,?)", (item.component_id, item.quantity, item.condition))
    c.commit(); c.close(); return {"ok": True}

@app.put("/api/inventory/{item_id}")
def update_item(item_id: int, u: InvUpdate):
    c = db.conn()
    cur = c.execute("UPDATE inventory SET quantity=?, condition=COALESCE(?, condition) WHERE id=?", (u.quantity, u.condition, item_id))
    c.commit(); c.close()
    if not cur.rowcount: raise HTTPException(404, "Inventory item not found")
    return {"ok": True}

@app.delete("/api/inventory/{item_id}", status_code=204)
def delete_item(item_id: int):
    c = db.conn(); cur = c.execute("DELETE FROM inventory WHERE id=?", (item_id,)); c.commit(); c.close()
    if not cur.rowcount: raise HTTPException(404, "Inventory item not found")

@app.delete("/api/inventory", status_code=204)
def clear():
    c = db.conn(); c.execute("DELETE FROM inventory"); c.commit(); c.close()

@app.post("/api/inventory/demo")
def load_demo(kit: str = "default"):
    kit_data = DEMO_KITS.get(kit, DEMO_KITS["default"])
    c = db.conn()
    c.execute("DELETE FROM inventory")
    for n, q in kit_data.items():
        cid = c.execute("SELECT id FROM components WHERE name=?", (n,)).fetchone()["id"]
        c.execute("INSERT INTO inventory(component_id,quantity,condition) VALUES(?,?,'Working')", (cid, q))
    c.commit(); c.close(); return {"ok": True, "kit": kit}

@app.get("/api/projects")
def projects():
    return [{k: p[k] for k in ("id", "name", "description", "difficulty", "estimated_cost", "estimated_waste_reuse_grams")} | {"components": [r["name"] for r in p["requirements"]]} for p in db.projects()]

@app.get("/api/projects/{pid}")
def project(pid: int):
    p = next((p for p in db.projects() if p["id"] == pid), None)
    if not p: raise HTTPException(404, "Project not found")
    return {**p, "match": evaluate(p, inv_map())}

@app.get("/api/recommendations")
def recommendations():
    return recommend(db.projects(), inv_map(), include_zero=False)

@app.get("/api/dashboard")
def dashboard():
    items, projs = inventory(), db.projects()
    recs = recommend(projs, inv_map())
    need = {}
    for p in projs:
        for r in p["requirements"]: need[r["component_id"]] = max(need.get(r["component_id"], 0), r["required"])
    reusable = [(i, min(i["quantity"], need.get(i["component_id"], 0))) for i in items]
    cats = {}
    for i in items: cats[i["category"]] = cats.get(i["category"], 0) + i["quantity"]
    return {"total_units": sum(i["quantity"] for i in items), "distinct": len(items), "projects_matched": len(recs),
            "ready_to_build": sum(r["score"] == 100 for r in recs), "units_reusable": sum(u for _, u in reusable),
            "waste_diverted_g": round(sum(u * i["estimated_weight_grams"] for i, u in reusable)),
            "categories": cats, "top_projects": [{"name": r["name"], "score": r["score"]} for r in recs[:8]]}

class SnapMatchIn(BaseModel):
    image_b64: str | None = None
    mode: str = "auto"
    api_key: str | None = None

@app.post("/api/snap-match")
def snap_match(data: SnapMatchIn | None = None):
    user_key = data.api_key.strip() if (data and data.api_key) else None
    api_key = user_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key and api_key.strip() in ("YOUR_API_KEY_HERE", "YOUR_GEMINI_API_KEY", ""):
        api_key = None

    # Explicit Demo Mode requested
    if data and (data.mode == "demo" or data.image_b64 == "demo"):
        c = db.conn()
        comps = [dict(x) for x in c.execute("SELECT id, name, category FROM components WHERE name IN ('Arduino Uno', 'Ultrasonic Sensor', 'Servo Motor', 'LED', 'Buzzer', 'Resistor')")]
        c.close()
        detected = [
            {"component_id": next((x["id"] for x in comps if x["name"]=="Arduino Uno"), 1), "name": "Arduino Uno", "category": "Microcontroller", "confidence": 94, "reason": "Predefined sample board for demonstration"},
            {"component_id": next((x["id"] for x in comps if x["name"]=="Ultrasonic Sensor"), 15), "name": "Ultrasonic Sensor", "category": "Sensor", "confidence": 88, "reason": "Predefined sample distance sensor for demonstration"},
            {"component_id": next((x["id"] for x in comps if x["name"]=="Servo Motor"), 12), "name": "Servo Motor", "category": "Actuator", "confidence": 91, "reason": "Predefined sample motor actuator for demonstration"},
            {"component_id": next((x["id"] for x in comps if x["name"]=="LED"), 6), "name": "LED", "category": "Output", "confidence": 97, "reason": "Predefined sample light indicator for demonstration"},
        ]
        return {
            "mode": "demo",
            "ai_available": bool(api_key),
            "message": "DEMO MODE: Predefined sample component dataset loaded for demonstration.",
            "detected": detected
        }

    # Real Image Analysis Path
    if data and data.image_b64 and data.image_b64 != "demo":
        if not api_key:
            return {
                "mode": "no_key",
                "ai_available": False,
                "message": "AI Vision is temporarily unavailable. Please use Demo Recognition.",
                "detected": []
            }

        try:
            import urllib.request, urllib.error, json, time, socket
            
            # 1. Parse image base64 & MIME type
            mime_type = "image/jpeg"
            if "," in data.image_b64:
                header, raw_b64 = data.image_b64.split(",", 1)
                if "data:" in header and ";base64" in header:
                    extracted_mime = header.split("data:")[1].split(";base64")[0]
                    if extracted_mime: mime_type = extracted_mime
            else:
                raw_b64 = data.image_b64

            b64_size_kb = len(raw_b64) / 1024.0
            print(f"[Snap&Match] Image received. MIME: {mime_type}, Base64 Payload Size: {b64_size_kb:.1f} KB")

            prompt_text = (
                "Analyze this image to identify electronic components. "
                "Match components strictly against this master catalog: Arduino Uno, Arduino Nano, ESP32, Raspberry Pi, LED, RGB LED, Resistor, Capacitor, Buzzer, Push Button, Servo Motor, DC Motor, Stepper Motor, Ultrasonic Sensor, IR Sensor, LDR Sensor, Temperature Sensor, Soil Moisture Sensor, Relay Module, LCD Display, OLED Display, Breadboard, Jumper Wires, Potentiometer, 9V Battery, Battery Holder, Old USB Cable, Old Computer Fan, Old Mobile Charger, Old Speaker, Old Webcam, Old Keyboard, Old Mouse.\n"
                "IMPORTANT: If the image does NOT contain recognizable electronic components, return an empty array {\"detections\": []}. Do NOT force or fabricate detections.\n"
                "Return ONLY a valid JSON object in this exact format: {\"detections\": [{\"name\": \"Arduino Uno\", \"confidence\": 94, \"quantity\": 1, \"reason\": \"Visible Arduino board layout and USB port\"}]}"
            )

            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_text},
                        {"inline_data": {"mime_type": mime_type, "data": raw_b64}}
                    ]
                }]
            }

            # 2. Build candidate model fallback list & timeout configuration
            env_model = os.environ.get("GEMINI_MODEL", "").strip()
            timeout_sec = int(os.environ.get("GEMINI_TIMEOUT", "45"))

            candidate_models = []
            if env_model:
                candidate_models.append(env_model)
            
            candidate_models.extend([
                "gemini-3.8-flash",
                "gemini-3.5-flash",
                "gemini-3.1-flash-lite",
                "gemini-flash-latest",
                "gemini-2.5-flash"
            ])
            
            models_to_try = []
            for m in candidate_models:
                if m and m not in models_to_try:
                    models_to_try.append(m)

            res_data = None
            last_err_detail = None
            used_model = None
            start_time = time.time()

            for m_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
                print(f"[Snap&Match] Requesting Gemini Vision API -> Model: '{m_name}' (Timeout: {timeout_sec}s)...")
                try:
                    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        used_model = m_name
                        elapsed = time.time() - start_time
                        print(f"[Snap&Match] Gemini Vision response received in {elapsed:.2f}s from model: '{used_model}'")
                        break
                except urllib.error.HTTPError as e:
                    last_err_detail = ("http", e.code, getattr(e, 'reason', ''))
                    print(f"[Snap&Match] HTTP Error {e.code} for model '{m_name}': {e.reason}")
                    if e.code in (404, 429, 503):
                        continue
                    else:
                        break
                except (urllib.error.URLError, socket.timeout, TimeoutError) as e:
                    err_str = str(e)
                    print(f"[Snap&Match] Network/Timeout error for model '{m_name}': {err_str}")
                    last_err_detail = ("timeout", 408, "Request timed out")
                    continue
                except Exception as e:
                    print(f"[Snap&Match] Unexpected error for model '{m_name}': {e}")
                    last_err_detail = ("error", 500, str(e))
                    break

            if not res_data:
                err_kind, code, reason = last_err_detail if last_err_detail else ("error", 500, "API request failed")
                if err_kind == "timeout":
                    err_msg = f"Gemini Vision network request timed out after {timeout_sec} seconds. High-resolution photos or Google API traffic spikes may cause network delays. Please retry or use Demo Mode."
                elif code in (401, 403):
                    err_msg = f"Gemini API authentication or permission problem (HTTP {code}). Please check your API key."
                elif code == 404:
                    err_msg = f"Gemini model or API endpoint was not found (HTTP 404). Configured model: '{models_to_try[0]}'."
                elif code == 429:
                    err_msg = f"Gemini API quota or rate limit reached (HTTP 429). Please wait a moment or use Demo Mode."
                elif code == 400:
                    err_msg = f"Gemini rejected the image or request format (HTTP 400)."
                elif code >= 500:
                    err_msg = f"Gemini service temporarily unavailable (HTTP {code}). Please try again shortly."
                else:
                    err_msg = f"Gemini API request failed (HTTP {code}: {reason})"

                return {
                    "mode": "error",
                    "ai_available": True,
                    "message": f"AI vision processing failed ({err_msg}).",
                    "detected": []
                }

            text = res_data["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = text.strip()
            if "```json" in clean_text:
                clean_text = clean_text.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_text:
                clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
            clean_json = clean_text[clean_text.find("{"):clean_text.rfind("}")+1]
            parsed = json.loads(clean_json)
            raw_detections = parsed.get("detections") or parsed.get("components") or []
            
            c = db.conn()
            out = []
            for item in raw_detections:
                item_name = item.get("name", "")
                if not item_name: continue
                row = c.execute("SELECT id, name, category FROM components WHERE LOWER(name) LIKE LOWER(?)", (f"%{item_name}%",)).fetchone()
                if row:
                    conf = item.get("confidence", 90)
                    try:
                        conf = float(conf)
                        if conf <= 1.0: conf = int(conf * 100)
                        else: conf = int(conf)
                    except (ValueError, TypeError):
                        conf = 90
                    out.append({
                        "component_id": row["id"],
                        "name": row["name"],
                        "category": row["category"],
                        "confidence": min(max(conf, 1), 100),
                        "reason": item.get("reason") or f"Identified as {row['name']} from image analysis"
                    })
            c.close()

            print(f"[Snap&Match] Parsed {len(out)} component detections: {[x['name'] for x in out]}")
            
            if not out:
                return {
                    "mode": "real_ai",
                    "ai_available": True,
                    "model_used": used_model,
                    "message": "No recognizable electronic components were confidently identified in this image. Please upload a clearer photo of electronic hardware.",
                    "detected": []
                }

            return {
                "mode": "real_ai",
                "ai_available": True,
                "model_used": used_model,
                "message": f"AI vision component recognition completed using model {used_model}.",
                "detected": out
            }
        except Exception as e:
            print("Gemini Vision API exception:", e)
            return {
                "mode": "error",
                "ai_available": True,
                "message": f"AI vision processing failed ({str(e)}). Please try again or use Demo Mode.",
                "detected": []
            }

    return {
        "mode": "no_image",
        "ai_available": bool(api_key),
        "message": "No image selected.",
        "detected": []
    }

class ChatIn(BaseModel):
    message: str
    project_id: int

@app.post("/api/chat")
def chat(data: ChatIn):
    p = next((p for p in db.projects() if p["id"] == data.project_id), None)
    if not p:
        raise HTTPException(404, "Project not found")

    m = evaluate(p, inv_map())
    
    # Build contextual prompt for Gemini
    missing_items = [f"{r['name']} (Required: {r['required']}, Available: {r['available']})" for r in m["requirements"] if r["status"] != "full"]
    matched_items = [f"{r['name']} (Available: {r['available']}/{r['required']})" for r in m["requirements"] if r["status"] == "full"]
    
    context_str = (
        f"PROJECT CONTEXT:\n"
        f"- Project Name: {p['name']}\n"
        f"- Description: {p['description']}\n"
        f"- Difficulty: {p['difficulty']}\n"
        f"- Estimated Cost: ₹{p['estimated_cost']}\n"
        f"- Additional Cost Needed: ₹{m['additional_cost']}\n"
        f"- Waste Reused: {m['waste_reused_g']}g\n"
        f"- Feasibility Score: {m['score']}%\n"
        f"- Completion Status: {m['completion_status']}\n"
        f"- Educational Value: {p.get('educational_value', 'N/A')}\n"
        f"- Why Recommended: {', '.join(m.get('why_recommended', []))}\n"
        f"- Matched/Available Components: {', '.join(matched_items) if matched_items else 'None'}\n"
        f"- Missing/Incomplete Components: {', '.join(missing_items) if missing_items else 'None (100% Complete)'}\n"
        f"- Assembly Build Steps:\n" + "\n".join([f"  {idx+1}. {step}" for idx, step in enumerate(p.get('build_steps', []))])
    )

    system_instruction = (
        "You are SecondLife Assistant, an AI assistant for an electronic component reuse platform. "
        "Your job is to help users understand electronic reuse projects and make practical decisions about reusing components. "
        "Answer using the project and inventory context provided below. "
        "Never invent components, project requirements, feasibility values, or inventory quantities. "
        "If information is not available, clearly say that it is not available. "
        "Prefer concise, practical explanations. "
        "When discussing missing components, clearly identify what is missing. "
        "When suggesting alternatives, clearly label them as suggestions and do not claim that an alternative is guaranteed to work. "
        "For electrical safety, provide conservative guidance and recommend appropriate supervision when needed. "
        "Keep responses focused on the SecondLife project."
    )

    user_query = data.message.strip()
    if not user_query:
        return {"ok": True, "reply": "Please ask a question about this project or your components."}

    full_prompt = f"{system_instruction}\n\n{context_str}\n\nUSER QUESTION: {user_query}"

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key.strip() in ("YOUR_API_KEY_HERE", "YOUR_GEMINI_API_KEY", ""):
        return {
            "ok": False,
            "reply": "AI Assistant is temporarily unavailable. You can still use SecondLife's project matching and inventory features."
        }

    env_model = os.environ.get("GEMINI_MODEL", "").strip()
    candidate_models = []
    if env_model: candidate_models.append(env_model)
    candidate_models.extend(["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest", "gemini-2.5-flash"])
    
    models_to_try = []
    for model_name in candidate_models:
        if model_name and model_name not in models_to_try:
            models_to_try.append(model_name)

    timeout_sec = int(os.environ.get("GEMINI_TIMEOUT", "30"))

    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }]
    }

    import urllib.request, urllib.error, json, socket
    res_data = None

    for m_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_name}:generateContent?key={api_key}"
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                break
        except urllib.error.HTTPError as e:
            if e.code in (404, 429, 503): continue
            else: break
        except Exception:
            continue

    if not res_data:
        return {
            "ok": False,
            "reply": "AI Assistant is temporarily unavailable. You can still use SecondLife's project matching and inventory features."
        }

    try:
        reply_text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return {"ok": True, "reply": reply_text}
    except Exception as e:
        print("Chat response parse error:", e)
        return {
            "ok": False,
            "reply": "AI Assistant is temporarily unavailable. You can still use SecondLife's project matching and inventory features."
        }

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")
@app.get("/")
def index(): return FileResponse(os.path.join(os.path.dirname(__file__), "static", "index.html"))


