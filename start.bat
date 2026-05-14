@echo off
title Lancement Projet Predictive Maintenance

echo ===============================
echo Lancement du Backend...
echo ===============================

start cmd /k "cd backend && ..\pfe\Scripts\activate && uvicorn app.main:app --reload"

timeout /t 5

echo ===============================
echo Lancement du Frontend...
echo ===============================

start cmd /k "cd frontend && npm run dev"

echo ===============================
echo Projet lancé !
echo ===============================

pause