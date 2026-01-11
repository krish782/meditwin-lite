from fastapi import APIRouter, File, UploadFile, HTTPException
from services.pdf_parser import extract_text_from_bytes
from services.document_classifier import classify_document_stub
from config import db
from datetime import datetime
from typing import Any         
import uuid
from services.gemini_client import summarize_text

router = APIRouter(prefix="/api", tags=["documents"])

# TEMP: fake current user id until auth is wired
def get_current_user_id() -> str:
    return "test-user-id"


def is_medical_document(text: str) -> tuple[bool, str]:
    """
    STRICT medical validation - document must have medical keywords
    Returns: (is_medical: bool, reason: str)
    """
    text = text.upper()

    # 🏥 MEDICAL KEYWORDS (MUST HAVE AT LEAST 2)
    medical_keywords = [
        "PATIENT", "HOSPITAL", "DOCTOR", "CLINICAL", "DIAGNOSIS",
        "GLUCOSE", "HBA1C", "BLOOD", "LAB", "REPORT", "PRESCRIPTION",
        "MEDICAL", "DISCHARGE", "SYMPTOM", "MEDICINE", "TEST", "RESULT",
        "HEMOGLOBIN", "CHOLESTEROL", "CREATININE", "THYROID", "URINE",
        "PATHOLOGY", "RADIOLOGY", "X-RAY", "CT", "MRI", "ULTRASOUND",
        "CONSULTATION", "TREATMENT", "SURGERY", "WARD", "OPD", "IPD"
    ]

    # 🚫 NON-MEDICAL KEYWORDS (AUTO-REJECT IF FOUND)
    non_medical_keywords = [
        "PNR", "TRAIN", "RAILWAY", "RESERVATION", "TICKET", "ERS",
        "IRCTC", "COACH", "BERTH", "PASSENGER", "JOURNEY", "PLATFORM",
        "INVOICE", "GST", "GSTIN", "TAX INVOICE", "BILL", "RECEIPT",
        "PURCHASE ORDER", "VENDOR", "CUSTOMER ID", "PAYMENT"
    ]

    # Count matches
    medical_matches = [kw for kw in medical_keywords if kw in text]
    non_medical_matches = [kw for kw in non_medical_keywords if kw in text]

    # RULE 1: Has non-medical keywords → REJECT
    if non_medical_matches:
        return False, f"Non-medical content detected: {', '.join(non_medical_matches[:3])}"

    # RULE 2: Needs at least 2 medical keywords to be accepted
    if len(medical_matches) < 2:
        return False, f"Insufficient medical content (found {len(medical_matches)} medical keywords, need 2+)"

    # RULE 3: Document is medical ✅
    return True, f"Medical document verified ({len(medical_matches)} medical keywords found)"


@router.post("/upload-document")
async def upload_document(file: UploadFile = File(...)):
    if file.content_type not in ["application/pdf"]:
        raise HTTPException(status_code=400, detail="Only PDFs supported")

    try:
        user_id = get_current_user_id()
        file_bytes = await file.read()
        raw_text = extract_text_from_bytes(file_bytes)
        
        # 🚨 STRICT MEDICAL VALIDATION
        is_medical, reason = is_medical_document(raw_text)
        
        if not is_medical:
            return {
                "success": False,
                "error": "NON-MEDICAL DOCUMENT REJECTED",
                "message": "❌ Only medical documents accepted (lab reports, prescriptions, discharge summaries)",
                "reason": reason
            }
        
        # ✅ MEDICAL DOCUMENT - PROCEED WITH CLASSIFICATION
        classification = classify_document_stub(raw_text.lower())
        doc_id = str(uuid.uuid4())
        doc_ref = db.collection("users").document(user_id).collection("documents").document(doc_id)
        
        doc_data = {
            "filename": file.filename,
            "uploadDate": datetime.utcnow(),
            "rawText": raw_text.lower(),
            "documentType": classification["documentType"],
            "isDiabetesReport": classification["isDiabetesReport"],
            "reportDate": classification["reportDate"],
            "metrics": classification["metrics"],
            "validationStatus": "MEDICAL_VERIFIED"  # Track that validation passed
        }
        
        doc_ref.set(doc_data)
        
        return {
            "success": True,
            "documentId": doc_id,
            "documentType": classification["documentType"],
            "validationStatus": reason  # Show why it was accepted
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/{document_id}")
async def get_document(document_id: str) -> Any:
    try:
        user_id = get_current_user_id()

        doc_ref = db.collection("users").document(user_id).collection("documents").document(document_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_data = doc_snapshot.to_dict()
        doc_data["id"] = document_id
        return doc_data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents() -> list[dict]:
    try:
        user_id = get_current_user_id()
        snapshots = db.collection("users").document(user_id).collection("documents").stream()

        documents = []
        for snap in snapshots:
            data = snap.to_dict()
            data["id"] = snap.id
            documents.append(data)

        return documents

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-gemini")
async def test_gemini():
    text = "This is a sample medical document about diabetes and blood sugar reports."
    summary = summarize_text(text)
    return {"summary": summary}


@router.get("/debug-models")
async def debug_models():
    import google.generativeai as genai
    models = genai.list_models()
    return {
        "available_models": [m.name for m in models if 'generateContent' in m.supported_generation_methods],
        "all_models": [m.name for m in models]
    }


# Replace the prompt in your /explain-document endpoint in routes/documents.py

# Add this function BEFORE your @router.get("/explain-document/{document_id}") in routes/documents.py

def generate_fallback_analysis(metrics: dict, text_preview: str) -> dict:
    """
    Generate analysis without calling AI (for quota limits or testing)
    Uses metrics and basic text analysis
    """
    analysis = {
        "summary": "",
        "keyFindings": [],
        "doctorQuestions": [],
        "recommendations": [],
        "criticalAlerts": None
    }
    
    # Generate summary based on metrics
    findings = []
    if metrics.get('hba1c'):
        hba1c_val = float(metrics['hba1c'].replace('%', ''))
        if hba1c_val >= 6.5:
            findings.append(f"HbA1c of {metrics['hba1c']} indicates diabetes")
        elif hba1c_val >= 5.7:
            findings.append(f"HbA1c of {metrics['hba1c']} indicates prediabetes")
        else:
            findings.append(f"HbA1c of {metrics['hba1c']} is in normal range")
    
    if metrics.get('glucose'):
        glucose_val = int(metrics['glucose'].split()[0])
        if glucose_val >= 126:
            findings.append(f"fasting glucose of {metrics['glucose']} is elevated (diabetes range)")
        elif glucose_val >= 100:
            findings.append(f"fasting glucose of {metrics['glucose']} is elevated (prediabetes range)")
    
    analysis["summary"] = f"Your lab results show {', '.join(findings) if findings else 'multiple health markers'}. " + \
                         f"{'Several values are outside normal ranges and need attention.' if len(findings) > 1 else 'Review the key findings below with your doctor.'}"
    
    # Generate key findings
    if metrics.get('hba1c'):
        hba1c_val = float(metrics['hba1c'].replace('%', ''))
        status = "elevated" if hba1c_val >= 5.7 else "normal"
        analysis["keyFindings"].append(
            f"HbA1c is {metrics['hba1c']} - {status} (normal range: 4.0-5.6%)"
        )
    
    if metrics.get('glucose'):
        glucose_val = int(metrics['glucose'].split()[0])
        status = "elevated" if glucose_val >= 100 else "normal"
        analysis["keyFindings"].append(
            f"Fasting glucose is {metrics['glucose']} - {status} (normal range: 70-100 mg/dL)"
        )
    
    if metrics.get('blood_pressure'):
        analysis["keyFindings"].append(
            f"Blood pressure is {metrics['blood_pressure']} (target: 120/80 mmHg or below)"
        )
    
    if metrics.get('cholesterol'):
        analysis["keyFindings"].append(
            f"Total cholesterol is {metrics['cholesterol']} (recommended: below 200 mg/dL)"
        )
    
    # Generate smart doctor questions based on actual values
    if metrics.get('hba1c'):
        hba1c_val = float(metrics['hba1c'].replace('%', ''))
        if hba1c_val >= 5.7:
            analysis["doctorQuestions"].append(
                f"My HbA1c is {metrics['hba1c']} which indicates {'diabetes' if hba1c_val >= 6.5 else 'prediabetes'} - should I start medication or can lifestyle changes help?"
            )
            analysis["doctorQuestions"].append(
                f"What specific dietary changes would be most effective to lower my HbA1c from {metrics['hba1c']}?"
            )
    
    if metrics.get('glucose'):
        glucose_val = int(metrics['glucose'].split()[0])
        if glucose_val >= 100:
            analysis["doctorQuestions"].append(
                f"My fasting glucose is {metrics['glucose']} - how often should I monitor my blood sugar at home?"
            )
            analysis["doctorQuestions"].append(
                f"Should I be concerned about my glucose level of {metrics['glucose']}? What are my next steps?"
            )
    
    if metrics.get('blood_pressure'):
        analysis["doctorQuestions"].append(
            f"My blood pressure is {metrics['blood_pressure']} - is this related to my blood sugar levels?"
        )
    
    # Add generic questions if we don't have enough
    while len(analysis["doctorQuestions"]) < 5:
        generic_questions = [
            "How soon should I have a follow-up test to monitor my progress?",
            "What lifestyle modifications would you recommend based on these results?",
            "Are there any medications I should consider given these values?",
            "Should I be tracking any other health metrics at home?",
            "What are realistic targets for me to aim for in the next 3-6 months?"
        ]
        for q in generic_questions:
            if q not in analysis["doctorQuestions"] and len(analysis["doctorQuestions"]) < 5:
                analysis["doctorQuestions"].append(q)
    
    # Generate recommendations
    if metrics.get('hba1c') or metrics.get('glucose'):
        analysis["recommendations"].extend([
            "Follow a balanced diet low in refined carbohydrates and added sugars",
            "Engage in at least 150 minutes of moderate exercise per week",
            "Monitor blood glucose levels as recommended by your doctor"
        ])
    
    analysis["recommendations"].extend([
        "Schedule a follow-up appointment to discuss these results in detail",
        "Keep a log of your diet, exercise, and any symptoms to share with your doctor"
    ])
    
    # Check for critical alerts
    critical = []
    if metrics.get('hba1c'):
        hba1c_val = float(metrics['hba1c'].replace('%', ''))
        if hba1c_val >= 9.0:
            critical.append("HbA1c is critically high - contact your doctor immediately")
    
    if metrics.get('glucose'):
        glucose_val = int(metrics['glucose'].split()[0])
        if glucose_val >= 200:
            critical.append("Fasting glucose is dangerously high - seek medical attention today")
    
    if critical:
        analysis["criticalAlerts"] = critical
    
    return analysis

# Add this function to your routes/documents.py (before explain_document endpoint)

def calculate_trends(current_doc_id: str, user_id: str, current_metrics: dict) -> dict:
    """
    Compare current document metrics with previous report
    Returns trend data with changes and directions
    """
    from datetime import datetime
    
    trends = {
        "hasPreviousReport": False,
        "previousDate": None,
        "changes": {}
    }
    
    try:
        # Get all documents for this user, sorted by date (newest first)
        docs_ref = db.collection("users").document(user_id).collection("documents")
        docs = docs_ref.order_by("uploadDate", direction="DESCENDING").limit(10).stream()
        
        # Convert to list
        all_docs = []
        for doc in docs:
            doc_data = doc.to_dict()
            doc_data['id'] = doc.id
            all_docs.append(doc_data)
        
        # Find current document index
        current_index = None
        for i, doc in enumerate(all_docs):
            if doc['id'] == current_doc_id:
                current_index = i
                break
        
        # If no current doc found or it's the only/first doc, no comparison
        if current_index is None or current_index >= len(all_docs) - 1:
            print("ℹ️ No previous report found for comparison")
            return trends
        
        # Get previous document
        previous_doc = all_docs[current_index + 1]
        previous_metrics = previous_doc.get('metrics') or {}
        
        if not previous_metrics:
            print("ℹ️ Previous report has no metrics")
            return trends
        
        trends["hasPreviousReport"] = True
        trends["previousDate"] = previous_doc.get('uploadDate')
        
        print(f"📊 Comparing with previous report from {trends['previousDate']}")
        
        # Compare HbA1c
        if current_metrics.get('hba1c') and previous_metrics.get('hba1c'):
            curr_val = float(current_metrics['hba1c'].replace('%', ''))
            prev_val = float(previous_metrics['hba1c'].replace('%', ''))
            change = curr_val - prev_val
            
            trends["changes"]["hba1c"] = {
                "current": current_metrics['hba1c'],
                "previous": previous_metrics['hba1c'],
                "change": round(change, 1),
                "changePercent": round((change / prev_val) * 100, 1) if prev_val > 0 else 0,
                "direction": "up" if change > 0.1 else "down" if change < -0.1 else "stable",
                "arrow": "↑" if change > 0.1 else "↓" if change < -0.1 else "→",
                "isImproving": change < -0.1  # Lower is better for HbA1c
            }
        
        # Compare Glucose
        if current_metrics.get('glucose') and previous_metrics.get('glucose'):
            curr_val = float(current_metrics['glucose'].split()[0])
            prev_val = float(previous_metrics['glucose'].split()[0])
            change = curr_val - prev_val
            
            trends["changes"]["glucose"] = {
                "current": current_metrics['glucose'],
                "previous": previous_metrics['glucose'],
                "change": int(change),
                "changePercent": round((change / prev_val) * 100, 1) if prev_val > 0 else 0,
                "direction": "up" if change > 5 else "down" if change < -5 else "stable",
                "arrow": "↑" if change > 5 else "↓" if change < -5 else "→",
                "isImproving": change < -5  # Lower is better for glucose
            }
        
        # Compare Blood Pressure
        if current_metrics.get('blood_pressure') and previous_metrics.get('blood_pressure'):
            curr_systolic = int(current_metrics['blood_pressure'].split('/')[0])
            prev_systolic = int(previous_metrics['blood_pressure'].split('/')[0])
            change = curr_systolic - prev_systolic
            
            trends["changes"]["blood_pressure"] = {
                "current": current_metrics['blood_pressure'],
                "previous": previous_metrics['blood_pressure'],
                "change": change,
                "direction": "up" if change > 5 else "down" if change < -5 else "stable",
                "arrow": "↑" if change > 5 else "↓" if change < -5 else "→",
                "isImproving": change < -5  # Lower is better for BP
            }
        
        # Compare Cholesterol
        if current_metrics.get('cholesterol') and previous_metrics.get('cholesterol'):
            curr_val = int(current_metrics['cholesterol'].split()[0])
            prev_val = int(previous_metrics['cholesterol'].split()[0])
            change = curr_val - prev_val
            
            trends["changes"]["cholesterol"] = {
                "current": current_metrics['cholesterol'],
                "previous": previous_metrics['cholesterol'],
                "change": change,
                "direction": "up" if change > 10 else "down" if change < -10 else "stable",
                "arrow": "↑" if change > 10 else "↓" if change < -10 else "→",
                "isImproving": change < -10  # Lower is better for cholesterol
            }
        
        print(f"✅ Trend comparison complete: {len(trends['changes'])} metrics compared")
        
    except Exception as e:
        print(f"⚠️ Error calculating trends: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return trends

# Add this function to your routes/documents.py (before explain_document endpoint)

def assess_metric_severity(metrics: dict) -> dict:
    """
    Assess severity of each metric value
    Returns severity levels and alerts for critical values
    """
    severity = {}
    critical_alerts = []
    
    # ═══════════════════════════════════════════════════════════
    # HbA1c SEVERITY
    # ═══════════════════════════════════════════════════════════
    if metrics.get('hba1c'):
        try:
            hba1c_val = float(metrics['hba1c'].replace('%', ''))
            
            if hba1c_val >= 9.0:
                severity['hba1c'] = {
                    "level": "CRITICAL",
                    "color": "red",
                    "label": "CRITICALLY HIGH",
                    "message": f"Your HbA1c of {metrics['hba1c']} is critically high"
                }
                critical_alerts.append(f"⚠️ URGENT: HbA1c {metrics['hba1c']} is critically high - contact your doctor immediately")
            elif hba1c_val >= 6.5:
                severity['hba1c'] = {
                    "level": "WARNING",
                    "color": "yellow",
                    "label": "DIABETES RANGE",
                    "message": f"HbA1c {metrics['hba1c']} indicates diabetes"
                }
                critical_alerts.append(f"⚠️ WARNING: HbA1c {metrics['hba1c']} is in diabetes range - discuss treatment with your doctor")
            elif hba1c_val >= 5.7:
                severity['hba1c'] = {
                    "level": "ELEVATED",
                    "color": "yellow",
                    "label": "PREDIABETES",
                    "message": f"HbA1c {metrics['hba1c']} indicates prediabetes"
                }
            else:
                severity['hba1c'] = {
                    "level": "NORMAL",
                    "color": "green",
                    "label": "NORMAL",
                    "message": f"HbA1c {metrics['hba1c']} is in normal range"
                }
        except:
            pass
    
    # ═══════════════════════════════════════════════════════════
    # GLUCOSE SEVERITY
    # ═══════════════════════════════════════════════════════════
    if metrics.get('glucose'):
        try:
            glucose_val = int(metrics['glucose'].split()[0])
            
            if glucose_val >= 200:
                severity['glucose'] = {
                    "level": "CRITICAL",
                    "color": "red",
                    "label": "DANGEROUSLY HIGH",
                    "message": f"Glucose {metrics['glucose']} is dangerously high"
                }
                critical_alerts.append(f"⚠️ URGENT: Fasting glucose {metrics['glucose']} is dangerously high - seek medical attention today")
            elif glucose_val >= 126:
                severity['glucose'] = {
                    "level": "WARNING",
                    "color": "red",
                    "label": "DIABETES RANGE",
                    "message": f"Glucose {metrics['glucose']} is in diabetes range"
                }
                critical_alerts.append(f"⚠️ WARNING: Fasting glucose {metrics['glucose']} indicates diabetes")
            elif glucose_val >= 100:
                severity['glucose'] = {
                    "level": "ELEVATED",
                    "color": "yellow",
                    "label": "ELEVATED",
                    "message": f"Glucose {metrics['glucose']} is elevated"
                }
            else:
                severity['glucose'] = {
                    "level": "NORMAL",
                    "color": "green",
                    "label": "NORMAL",
                    "message": f"Glucose {metrics['glucose']} is in normal range"
                }
        except:
            pass
    
    # ═══════════════════════════════════════════════════════════
    # BLOOD PRESSURE SEVERITY
    # ═══════════════════════════════════════════════════════════
    if metrics.get('blood_pressure'):
        try:
            bp_parts = metrics['blood_pressure'].split('/')
            systolic = int(bp_parts[0])
            diastolic = int(bp_parts[1].split()[0])
            
            if systolic >= 180 or diastolic >= 120:
                severity['blood_pressure'] = {
                    "level": "CRITICAL",
                    "color": "red",
                    "label": "HYPERTENSIVE CRISIS",
                    "message": f"BP {metrics['blood_pressure']} is critically high"
                }
                critical_alerts.append(f"⚠️ URGENT: Blood pressure {metrics['blood_pressure']} requires immediate medical attention")
            elif systolic >= 140 or diastolic >= 90:
                severity['blood_pressure'] = {
                    "level": "WARNING",
                    "color": "red",
                    "label": "HYPERTENSION",
                    "message": f"BP {metrics['blood_pressure']} indicates hypertension"
                }
                critical_alerts.append(f"⚠️ WARNING: Blood pressure {metrics['blood_pressure']} indicates Stage 2 hypertension")
            elif systolic >= 130 or diastolic >= 80:
                severity['blood_pressure'] = {
                    "level": "ELEVATED",
                    "color": "yellow",
                    "label": "ELEVATED",
                    "message": f"BP {metrics['blood_pressure']} is elevated"
                }
            else:
                severity['blood_pressure'] = {
                    "level": "NORMAL",
                    "color": "green",
                    "label": "NORMAL",
                    "message": f"BP {metrics['blood_pressure']} is normal"
                }
        except:
            pass
    
    # ═══════════════════════════════════════════════════════════
    # CHOLESTEROL SEVERITY
    # ═══════════════════════════════════════════════════════════
    if metrics.get('cholesterol'):
        try:
            chol_val = int(metrics['cholesterol'].split()[0])
            
            if chol_val >= 240:
                severity['cholesterol'] = {
                    "level": "WARNING",
                    "color": "red",
                    "label": "HIGH",
                    "message": f"Cholesterol {metrics['cholesterol']} is high"
                }
                critical_alerts.append(f"⚠️ WARNING: Total cholesterol {metrics['cholesterol']} is high - increases heart disease risk")
            elif chol_val >= 200:
                severity['cholesterol'] = {
                    "level": "ELEVATED",
                    "color": "yellow",
                    "label": "BORDERLINE HIGH",
                    "message": f"Cholesterol {metrics['cholesterol']} is borderline high"
                }
            else:
                severity['cholesterol'] = {
                    "level": "NORMAL",
                    "color": "green",
                    "label": "DESIRABLE",
                    "message": f"Cholesterol {metrics['cholesterol']} is desirable"
                }
        except:
            pass
    
    return {
        "severity": severity,
        "criticalAlerts": critical_alerts if critical_alerts else None,
        "hasCritical": any(s.get("level") == "CRITICAL" for s in severity.values()),
        "hasWarning": any(s.get("level") in ["CRITICAL", "WARNING"] for s in severity.values())
    }

@router.get("/explain-document/{document_id}")
async def explain_document(document_id: str) -> dict:
    """
    Generate AI analysis for medical document
    """
    try:
        import json, re

        user_id = get_current_user_id()
        doc_ref = db.collection("users").document(user_id).collection("documents").document(document_id)
        doc_snapshot = doc_ref.get()

        if not doc_snapshot.exists:
            raise HTTPException(status_code=404, detail="Document not found")

        doc_data = doc_snapshot.to_dict()
        raw_text = doc_data.get("rawText", "")
        metrics = doc_data.get("metrics") or {}

        if not raw_text:
            raise HTTPException(status_code=400, detail="No text found in document")

        print(f"📄 Analyzing document: {doc_data.get('filename')}")
        print(f"📊 Document has {len(metrics)} metrics extracted")
        
        # 📈 CALCULATE TRENDS
        try:
            trends = calculate_trends(document_id, user_id, metrics)
            print(f"📈 Trend analysis: {trends.get('hasPreviousReport', False)}")
        except Exception as trend_err:
            print(f"⚠️ Trend calculation failed: {str(trend_err)}")
            trends = {"hasPreviousReport": False, "previousDate": None, "changes": {}}

        # CALCULATE SEVERITY
        try:
            severity_data = assess_metric_severity(metrics)
            print(f"🚨 Severity assessment: {severity_data.get('hasCritical', False)} critical, {severity_data.get('hasWarning', False)} warnings")
        except Exception as severity_err:
            print(f"⚠️ Severity assessment failed: {str(severity_err)}")
            severity_data = {"severity": {}, "criticalAlerts": None, "hasCritical": False, "hasWarning": False}

        # BUILD AI PROMPT
        metrics_summary = "\n".join([f"- {k.upper()}: {v}" for k, v in metrics.items()]) if metrics else "No metrics extracted yet"
        
        prompt = f"""Analyze this medical lab report. You MUST provide ALL 5 fields in your response.


REPORT TEXT:
{raw_text[:3000]}

EXTRACTED VALUES:
{metrics_summary}

Create a JSON response with these REQUIRED fields:

1. "summary": Brief overview in 2-3 sentences
2. "keyFindings": Array of 4 findings about specific test values
3. "doctorQuestions": Array of exactly 5 questions the patient should ask their doctor. Each question MUST start with the patient's actual value (e.g., "My HbA1c is 6.8%..."). Make them specific and actionable.
4. "recommendations": Array of exactly 5 action steps
5. "criticalAlerts": null (or array if urgent)

CRITICAL: You MUST include doctorQuestions field with 5 specific questions that reference the actual test values.

Example doctorQuestions format:
[
  "My HbA1c is 6.8% which indicates prediabetes - should I start medication now or try lifestyle changes first?",
  "My fasting glucose is 128 mg/dL - what specific dietary changes would help bring this down to under 100?",
  "Should I be monitoring my blood sugar at home? If so, how often and what target numbers should I aim for?",
  "My blood pressure is 135/85 mmHg - is this related to my blood sugar issues?",
  "How soon should I have another HbA1c test to check if my changes are working?"
]

Return ONLY this JSON (no markdown, no code blocks):
{{"summary":"...","keyFindings":["..."],"doctorQuestions":["..."],"recommendations":["..."],"criticalAlerts":null}}"""

        print(f"📤 Sending prompt to Gemini AI...")
        
        # Call Gemini AI
        try:
            ai_response = summarize_text(prompt)
            print(f"📥 Received AI response: {len(ai_response)} characters")
        except Exception as gemini_error:
            error_str = str(gemini_error)
            print(f"❌ Gemini API error: {error_str}")
            
            # Check if it's a quota error
            if "429" in error_str or "quota" in error_str.lower():
                print(f"⚠️ Gemini quota exceeded, generating fallback response...")
                fallback_analysis = generate_fallback_analysis(metrics, raw_text[:500])
                
                return {
                    "success": True,
                    "documentId": document_id,
                    "filename": doc_data.get("filename"),
                    "metrics": metrics,
                    "trends": trends,
                    "severity": severity_data,
                    "aiAnalysis": fallback_analysis,
                    "note": "Generated using fallback due to API quota limit"
                }
            else:
                # Other Gemini error - raise it with details
                raise HTTPException(
                    status_code=500, 
                    detail=f"AI service error: {error_str}"
                )

        # Parse JSON response
        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
        if json_match:
            try:
                analysis = json.loads(json_match.group())
                
                # Validate and add defaults for missing fields
                required_fields = ["summary", "keyFindings", "doctorQuestions", "recommendations"]
                for field in required_fields:
                    if field not in analysis or not analysis[field]:
                        print(f"⚠️ Missing field '{field}', adding smart default")
                        
                        if field == "summary":
                            analysis[field] = "Analysis completed. Please review the findings below."
                        elif field == "doctorQuestions":
                            default_questions = []
                            if metrics.get('hba1c'):
                                default_questions.append(f"My HbA1c is {metrics['hba1c']} - what does this mean for my diabetes risk?")
                                default_questions.append(f"Should I start medication or can lifestyle changes help control my HbA1c of {metrics['hba1c']}?")
                            if metrics.get('glucose'):
                                default_questions.append(f"My fasting glucose is {metrics['glucose']} - what dietary changes would help most?")
                            if not default_questions:
                                default_questions = [
                                    "What do these results mean for my overall health?",
                                    "Should I make any lifestyle changes based on these findings?",
                                    "How often should I retest these values?"
                                ]
                            analysis[field] = default_questions[:5]
                        else:
                            analysis[field] = []
                
                if "criticalAlerts" not in analysis:
                    analysis["criticalAlerts"] = None
                
                print(f"✅ Analysis complete - {len(analysis.get('doctorQuestions', []))} questions generated")
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON Parse Error: {e}")
                print(f"Raw AI response: {ai_response[:500]}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to parse AI response: {str(e)}"
                )
        else:
            print(f"❌ No JSON found in AI response")
            print(f"Raw response: {ai_response[:500]}")
            raise HTTPException(
                status_code=500,
                detail="AI response was not in expected JSON format"
            )

        return {
            "success": True,
            "documentId": document_id,
            "filename": doc_data.get("filename"),
            "metrics": metrics,
            "trends": trends,
            "severity": severity_data,
            "aiAnalysis": analysis
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Unexpected error in explain_document: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Analysis failed: {str(e)}"
        )
    # At the end of your routes/documents.py file, add:

@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document from Firestore"""
    try:
        user_id = get_current_user_id()
        doc_ref = db.collection("users").document(user_id).collection("documents").document(document_id)
        
        doc_snapshot = doc_ref.get()
        if not doc_snapshot.exists:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_ref.delete()
        
        return {
            "success": True,
            "message": "Document deleted successfully",
            "documentId": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
    
    # Add this endpoint to your routes/documents.py

@router.get("/chart-data")
async def get_chart_data():
    """
    Get historical metrics data for charts
    Returns time-series data for HbA1c, Glucose, BP, Cholesterol
    """
    try:
        user_id = get_current_user_id()
        
        # Get all documents ordered by date (oldest first for charts)
        docs_ref = db.collection("users").document(user_id).collection("documents")
        docs = docs_ref.order_by("uploadDate", direction="ASCENDING").stream()
        
        chart_data = {
            "hba1c": [],
            "glucose": [],
            "blood_pressure": [],
            "cholesterol": [],
            "timeline": []
        }
        
        for doc in docs:
            doc_data = doc.to_dict()
            metrics = doc_data.get('metrics') or {}
            upload_date = doc_data.get('uploadDate')
            
            if not upload_date or not metrics:
                continue
            
            # Format date for display
            date_str = upload_date.strftime('%m/%d') if hasattr(upload_date, 'strftime') else str(upload_date)[:10]
            
            # Extract HbA1c
            if metrics.get('hba1c'):
                hba1c_val = float(metrics['hba1c'].replace('%', ''))
                chart_data['hba1c'].append({
                    "date": date_str,
                    "value": hba1c_val,
                    "label": f"{hba1c_val}%"
                })
            
            # Extract Glucose
            if metrics.get('glucose'):
                glucose_val = int(metrics['glucose'].split()[0])
                chart_data['glucose'].append({
                    "date": date_str,
                    "value": glucose_val,
                    "label": f"{glucose_val} mg/dL"
                })
            
            # Extract Blood Pressure (systolic)
            if metrics.get('blood_pressure'):
                bp_systolic = int(metrics['blood_pressure'].split('/')[0])
                chart_data['blood_pressure'].append({
                    "date": date_str,
                    "value": bp_systolic,
                    "label": metrics['blood_pressure']
                })
            
            # Extract Cholesterol
            if metrics.get('cholesterol'):
                chol_val = int(metrics['cholesterol'].split()[0])
                chart_data['cholesterol'].append({
                    "date": date_str,
                    "value": chol_val,
                    "label": f"{chol_val} mg/dL"
                })
            
            # Add to timeline
            if metrics:
                chart_data['timeline'].append({
                    "date": date_str,
                    "filename": doc_data.get('filename', 'Report'),
                    "documentType": doc_data.get('documentType', 'OTHER')
                })
        
        return {
            "success": True,
            "data": chart_data,
            "dataPoints": {
                "hba1c": len(chart_data['hba1c']),
                "glucose": len(chart_data['glucose']),
                "blood_pressure": len(chart_data['blood_pressure']),
                "cholesterol": len(chart_data['cholesterol'])
            }
        }
        
    except Exception as e:
        print(f"❌ Error fetching chart data: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to fetch chart data: {str(e)}")