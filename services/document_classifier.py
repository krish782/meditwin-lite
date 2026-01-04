"""
Enhanced document classifier with metrics extraction
Replace your entire services/document_classifier.py with this file
"""

import re
from typing import Dict, Any, Optional
from datetime import datetime


def extract_medical_metrics(text: str) -> Dict[str, Any]:
    """
    Extract medical metrics from lab report text
    Returns dict with hba1c, glucose, and other common metrics
    """
    text_upper = text.upper()
    metrics = {}
    
    # ═══════════════════════════════════════════════════════════
    # HbA1c EXTRACTION
    # ═══════════════════════════════════════════════════════════
    hba1c_patterns = [
        r'HBA1C[:\s]*\(.*?\)\s*(\d+\.?\d*)\s*%',  # HbA1c (Glycated Hemoglobin) 6.8%
        r'HBA1C[:\s]*(\d+\.?\d*)\s*%',           # HbA1c: 6.5%
        r'HBA1C[:\s]*(\d+\.?\d*)',               # HbA1c: 6.5
        r'GLYCATED\s+HEMOGLOBIN[:\s]*(\d+\.?\d*)\s*%',  # Glycated Hemoglobin: 6.5%
        r'A1C[:\s]*(\d+\.?\d*)\s*%',             # A1C: 6.5%
        r'HEMOGLOBIN\s+A1C[:\s]*(\d+\.?\d*)',    # Hemoglobin A1C: 6.5
    ]
    
    for pattern in hba1c_patterns:
        match = re.search(pattern, text_upper)
        if match:
            value = float(match.group(1))
            metrics['hba1c'] = f"{value}%"
            break
    
    # ═══════════════════════════════════════════════════════════
    # GLUCOSE EXTRACTION (Multiple formats)
    # ═══════════════════════════════════════════════════════════
    glucose_patterns = [
        # Fasting Blood Glucose with units separated
        r'FASTING\s+BLOOD\s+GLUCOSE\s+(\d+)\s+MG[/\s]*DL',  # Fasting Blood Glucose 128 mg/dL or MG DL
        r'FASTING\s+(?:BLOOD\s+)?GLUCOSE[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',
        r'FBS[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',     # FBS: 120 mg/dL
        r'FBG[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',     # FBG: 120
        
        # Random Blood Glucose
        r'RANDOM\s+(?:BLOOD\s+)?GLUCOSE[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',
        r'RBS[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',     # RBS: 140
        
        # General Blood Glucose
        r'BLOOD\s+GLUCOSE[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',
        r'GLUCOSE[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',
        r'BLOOD\s+SUGAR[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',
    ]
    
    for pattern in glucose_patterns:
        match = re.search(pattern, text_upper)
        if match:
            value = int(match.group(1))
            metrics['glucose'] = f"{value} mg/dL"
            break
    
    # ═══════════════════════════════════════════════════════════
    # ADDITIONAL COMMON METRICS
    # ═══════════════════════════════════════════════════════════
    
    # Blood Pressure
    bp_pattern = r'(?:BLOOD\s+PRESSURE|BP)[:\s]*(\d{2,3})/(\d{2,3})\s*(?:MMHG|MM HG)?'
    bp_match = re.search(bp_pattern, text_upper)
    if bp_match:
        systolic, diastolic = bp_match.groups()
        metrics['blood_pressure'] = f"{systolic}/{diastolic} mmHg"
    
    # Cholesterol
    cholesterol_patterns = [
        r'TOTAL\s+CHOLESTEROL[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',
        r'CHOLESTEROL[:\s]*(\d+)\s*(?:MG/DL|MGDL)?',
    ]
    for pattern in cholesterol_patterns:
        match = re.search(pattern, text_upper)
        if match:
            metrics['cholesterol'] = f"{match.group(1)} mg/dL"
            break
    
    # Hemoglobin
    hemoglobin_patterns = [
        r'HEMOGLOBIN[:\s]*(\d+\.?\d*)\s*(?:G/DL|GDL|GM/DL)?',
        r'HB[:\s]*(\d+\.?\d*)\s*(?:G/DL|GDL)?',
    ]
    for pattern in hemoglobin_patterns:
        match = re.search(pattern, text_upper)
        if match:
            metrics['hemoglobin'] = f"{match.group(1)} g/dL"
            break
    
    # Creatinine
    creatinine_pattern = r'CREATININE[:\s]*(\d+\.?\d*)\s*(?:MG/DL|MGDL)?'
    creatinine_match = re.search(creatinine_pattern, text_upper)
    if creatinine_match:
        metrics['creatinine'] = f"{creatinine_match.group(1)} mg/dL"
    
    return metrics


def extract_report_date(text: str) -> Optional[str]:
    """
    Extract report date from text
    Returns ISO format date string or None
    """
    text_upper = text.upper()
    
    # Date patterns
    date_patterns = [
        r'(?:REPORT\s+DATE|DATE)[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'(?:REPORT\s+DATE|DATE)[:\s]*(\d{1,2}\s+(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[A-Z]*\s+\d{2,4})',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',  # Fallback: any date
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text_upper)
        if match:
            date_str = match.group(1)
            # Try to parse and convert to ISO format
            try:
                # Handle various date formats
                for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%d-%m-%y', '%d/%m/%y']:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        return dt.isoformat()
                    except:
                        continue
            except:
                return date_str  # Return as-is if parsing fails
    
    return None


def classify_document_stub(text: str) -> Dict[str, Any]:
    """
    Enhanced document classifier with proper metrics extraction
    """
    text_upper = text.upper()
    
    # Extract metrics
    metrics = extract_medical_metrics(text)
    
    # Determine if it's a diabetes report
    is_diabetes = bool(metrics.get('hba1c') or metrics.get('glucose'))
    
    # Determine document type
    document_type = "OTHER"
    
    if is_diabetes:
        document_type = "DIABETES_LAB_REPORT"
    elif "DISCHARGE" in text_upper and "SUMMARY" in text_upper:
        document_type = "DISCHARGE_SUMMARY"
    elif "PRESCRIPTION" in text_upper:
        document_type = "PRESCRIPTION"
    elif "LAB" in text_upper or "REPORT" in text_upper:
        document_type = "LAB_REPORT"
    
    # Extract report date
    report_date = extract_report_date(text)
    
    return {
        "documentType": document_type,
        "isDiabetesReport": is_diabetes,
        "reportDate": report_date,
        "metrics": metrics  # This now contains actual extracted values!
    }


# ═══════════════════════════════════════════════════════════
# TESTING FUNCTION
# ═══════════════════════════════════════════════════════════

def test_extraction():
    """Test the extraction with sample text"""
    
    test_cases = [
        {
            "name": "Lab Report Format 1",
            "text": """
                CITY HOSPITAL LABORATORY
                Patient: John Doe
                Report Date: 02-01-2025
                
                TEST RESULTS:
                HbA1c: 6.8%
                Fasting Blood Glucose: 128 mg/dL
                Total Cholesterol: 210 mg/dL
                Blood Pressure: 135/85 mmHg
            """
        },
        {
            "name": "Lab Report Format 2",
            "text": """
                DIABETES SCREENING REPORT
                Date: 02/01/2025
                
                Glycated Hemoglobin (HbA1c): 7.2 %
                FBS: 145 mg/dL
                Hemoglobin: 13.5 g/dL
            """
        },
        {
            "name": "Lab Report Format 3",
            "text": """
                METABOLIC PANEL
                A1C: 6.5%
                Random Blood Sugar: 160
                BP: 120/80
                Creatinine: 1.2 mg/dL
            """
        }
    ]
    
    print("\n" + "="*70)
    print("🧪 TESTING METRICS EXTRACTION")
    print("="*70 + "\n")
    
    for test in test_cases:
        print(f"\n📄 Test: {test['name']}")
        print("-" * 70)
        
        result = classify_document_stub(test['text'])
        
        print(f"Document Type: {result['documentType']}")
        print(f"Is Diabetes Report: {result['isDiabetesReport']}")
        print(f"Report Date: {result['reportDate']}")
        print(f"\nExtracted Metrics:")
        
        if result['metrics']:
            for key, value in result['metrics'].items():
                print(f"  • {key.upper()}: {value}")
        else:
            print("  (No metrics found)")
    
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_extraction()