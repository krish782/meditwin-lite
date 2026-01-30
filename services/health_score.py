from datetime import datetime

def calculate_health_score(metrics: dict) -> dict:
    """
    Calculate overall health score (0-100) and risk assessments
    """
    score = 100
    risks = {
        "diabetes": {"level": "LOW", "score": 0, "color": "green"},
        "heart": {"level": "LOW", "score": 0, "color": "green"},
        "kidney": {"level": "LOW", "score": 0, "color": "green"}
    }
    components = {}
    
    # HbA1c Assessment (30% weight)
    if metrics.get('hba1c'):
        hba1c_val = float(metrics['hba1c'].replace('%', ''))
        
        if hba1c_val < 5.7:
            hba1c_score = 100
            diabetes_risk = 5
        elif hba1c_val < 6.5:
            hba1c_score = 70
            diabetes_risk = 40
        elif hba1c_val < 7.5:
            hba1c_score = 50
            diabetes_risk = 75
        elif hba1c_val < 9.0:
            hba1c_score = 30
            diabetes_risk = 90
        else:
            hba1c_score = 10
            diabetes_risk = 95
        
        components['hba1c'] = {
            "score": hba1c_score,
            "weight": 30,
            "contribution": hba1c_score * 0.3
        }
        score -= (100 - hba1c_score) * 0.3
        risks["diabetes"]["score"] = diabetes_risk
    
    # Glucose Assessment (25% weight)
    if metrics.get('glucose'):
        glucose_val = int(metrics['glucose'].split()[0])
        
        if glucose_val < 100:
            glucose_score = 100
            diabetes_risk_glucose = 5
        elif glucose_val < 126:
            glucose_score = 65
            diabetes_risk_glucose = 35
        elif glucose_val < 150:
            glucose_score = 45
            diabetes_risk_glucose = 70
        elif glucose_val < 200:
            glucose_score = 25
            diabetes_risk_glucose = 85
        else:
            glucose_score = 10
            diabetes_risk_glucose = 95
        
        components['glucose'] = {
            "score": glucose_score,
            "weight": 25,
            "contribution": glucose_score * 0.25
        }
        score -= (100 - glucose_score) * 0.25
        
        # Average diabetes risk from both metrics
        if 'diabetes' in risks and risks['diabetes']['score'] > 0:
            risks["diabetes"]["score"] = (risks["diabetes"]["score"] + diabetes_risk_glucose) / 2
        else:
            risks["diabetes"]["score"] = diabetes_risk_glucose
    
    # Blood Pressure Assessment (25% weight)
    if metrics.get('blood_pressure'):
        bp_parts = metrics['blood_pressure'].split('/')
        systolic = int(bp_parts[0])
        diastolic = int(bp_parts[1].split()[0])
        
        if systolic < 120 and diastolic < 80:
            bp_score = 100
            heart_risk = 5
        elif systolic < 130 or diastolic < 85:
            bp_score = 75
            heart_risk = 25
        elif systolic < 140 or diastolic < 90:
            bp_score = 50
            heart_risk = 55
        elif systolic < 180 or diastolic < 120:
            bp_score = 25
            heart_risk = 80
        else:
            bp_score = 10
            heart_risk = 95
        
        components['blood_pressure'] = {
            "score": bp_score,
            "weight": 25,
            "contribution": bp_score * 0.25
        }
        score -= (100 - bp_score) * 0.25
        risks["heart"]["score"] = heart_risk
    
    # Cholesterol Assessment (20% weight)
    if metrics.get('cholesterol'):
        chol_val = int(metrics['cholesterol'].split()[0])
        
        if chol_val < 200:
            chol_score = 100
            heart_risk_chol = 10
        elif chol_val < 240:
            chol_score = 65
            heart_risk_chol = 45
        else:
            chol_score = 35
            heart_risk_chol = 75
        
        components['cholesterol'] = {
            "score": chol_score,
            "weight": 20,
            "contribution": chol_score * 0.20
        }
        score -= (100 - chol_score) * 0.20
        
        # Average heart risk
        if risks["heart"]["score"] > 0:
            risks["heart"]["score"] = (risks["heart"]["score"] + heart_risk_chol) / 2
        else:
            risks["heart"]["score"] = heart_risk_chol
    
    # Determine risk levels and colors
    for risk_type in risks:
        risk_score = risks[risk_type]["score"]
        if risk_score < 25:
            risks[risk_type]["level"] = "LOW"
            risks[risk_type]["color"] = "green"
        elif risk_score < 50:
            risks[risk_type]["level"] = "MODERATE"
            risks[risk_type]["color"] = "yellow"
        elif risk_score < 75:
            risks[risk_type]["level"] = "HIGH"
            risks[risk_type]["color"] = "orange"
        else:
            risks[risk_type]["level"] = "CRITICAL"
            risks[risk_type]["color"] = "red"
    
    # Generate action items
    action_items = generate_action_items(metrics, risks)
    
    # Generate predictions
    predictions = generate_predictions(metrics, score)
    
    return {
        "overallScore": round(score, 1),
        "grade": get_health_grade(score),
        "components": components,
        "risks": risks,
        "actionItems": action_items,
        "predictions": predictions,
        "lastCalculated": datetime.utcnow().isoformat()
    }


def get_health_grade(score: float) -> str:
    """Convert score to letter grade"""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 70:
        return "C"
    elif score >= 60:
        return "D"
    else:
        return "F"


def generate_action_items(metrics: dict, risks: dict) -> list:
    """Generate personalized action items based on metrics and risks"""
    actions = []
    
    # Diabetes-related actions
    if risks["diabetes"]["level"] in ["HIGH", "CRITICAL"]:
        if metrics.get('hba1c'):
            hba1c_val = float(metrics['hba1c'].replace('%', ''))
            target = max(5.7, hba1c_val - 1.0)
            actions.append({
                "priority": "HIGH",
                "icon": "🎯",
                "title": "Lower HbA1c",
                "description": f"Reduce HbA1c from {metrics['hba1c']} to below {target}%",
                "timeline": "3 months",
                "steps": [
                    "Reduce refined carbohydrate intake by 50%",
                    "Exercise 30 minutes daily, 5 days/week",
                    "Monitor blood sugar twice daily"
                ]
            })
        
        if metrics.get('glucose'):
            actions.append({
                "priority": "HIGH",
                "icon": "🍽️",
                "title": "Control Fasting Glucose",
                "description": f"Bring fasting glucose from {metrics['glucose']} to under 100 mg/dL",
                "timeline": "6 weeks",
                "steps": [
                    "Eliminate sugary drinks completely",
                    "Eat high-fiber breakfast within 1 hour of waking",
                    "Take 10-minute walk after each meal"
                ]
            })
    
    # Heart health actions
    if risks["heart"]["level"] in ["HIGH", "CRITICAL"]:
        if metrics.get('blood_pressure'):
            actions.append({
                "priority": "HIGH",
                "icon": "❤️",
                "title": "Lower Blood Pressure",
                "description": f"Reduce BP from {metrics['blood_pressure']} to under 120/80 mmHg",
                "timeline": "8 weeks",
                "steps": [
                    "Reduce sodium intake to under 1500mg/day",
                    "Practice deep breathing 10 minutes daily",
                    "Aim for 7-8 hours sleep nightly"
                ]
            })
        
        if metrics.get('cholesterol'):
            chol_val = int(metrics['cholesterol'].split()[0])
            if chol_val >= 200:
                actions.append({
                    "priority": "MEDIUM",
                    "icon": "🥗",
                    "title": "Improve Cholesterol",
                    "description": f"Lower total cholesterol from {metrics['cholesterol']} to under 200 mg/dL",
                    "timeline": "12 weeks",
                    "steps": [
                        "Add 2 servings of fatty fish per week",
                        "Replace saturated fats with olive oil",
                        "Eat a handful of nuts daily"
                    ]
                })
    
    # General wellness actions
    actions.append({
        "priority": "MEDIUM",
        "icon": "📅",
        "title": "Schedule Follow-up",
        "description": "Book appointment with your doctor to discuss these results",
        "timeline": "This week",
        "steps": [
            "Bring this analysis to your appointment",
            "Ask about medication adjustments if needed",
            "Set up next lab test date (typically 3 months)"
        ]
    })
    
    return actions[:4]  # Return top 4 priority actions


def generate_predictions(metrics: dict, current_score: float) -> dict:
    """Generate health predictions based on current trajectory"""
    predictions = {}
    
    # If we have HbA1c
    if metrics.get('hba1c'):
        hba1c_val = float(metrics['hba1c'].replace('%', ''))
        
        if hba1c_val >= 5.7:
            # Calculate time to reach normal range (5.6%)
            # Assume 0.5% reduction per 3 months with lifestyle changes
            months_to_normal = int(((hba1c_val - 5.6) / 0.5) * 3)
            
            predictions["hba1c"] = {
                "metric": "HbA1c",
                "current": metrics['hba1c'],
                "target": "5.6%",
                "estimated_time": f"{months_to_normal} months",
                "message": f"With consistent lifestyle changes, you could reach normal HbA1c in {months_to_normal} months"
            }
    
    # Score improvement prediction
    if current_score < 75:
        target_score = 75
        score_gap = target_score - current_score
        months_to_target = max(3, int((score_gap / 5)))  # 5 points per month improvement
        
        predictions["overall"] = {
            "currentScore": round(current_score, 1),
            "targetScore": target_score,
            "estimatedTime": f"{months_to_target} months",
            "message": f"You could improve your health score to {target_score}/100 in {months_to_target} months"
        }
    
    return predictions