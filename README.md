# 🧬 MediTwin Lite

MediTwin Lite is an AI-powered healthcare platform that helps patients understand medical reports using Google Gemini AI.

## 🚀 Problem
Patients receive complex medical reports but don’t understand what they mean. Doctors have limited time to explain everything.

## 💡 Solution
MediTwin Lite allows users to upload medical reports and instantly receive AI-generated explanations, insights, and questions to ask their doctor.

## 🏗️ System Architecture

User  
→ Next.js Frontend  
→ FastAPI Backend  
→ Google Gemini Pro API  
→ Firebase Firestore Database  

## 🔁 Process Flow
1. User uploads medical report  
2. Backend extracts text  
3. Gemini AI analyzes the report  
4. Insights stored in Firestore  
5. User views results on dashboard  

## 🧰 Tech Stack
- Frontend: Next.js
- Backend: FastAPI
- AI: Google Gemini Pro
- Database: Firebase Firestore
- Auth: Firebase Auth

## 🛣️ Roadmap
- Multi-disease support
- Doctor dashboard
- Telemedicine integration
- Predictive health analytics

## 👥 Team
Stranger Coders
