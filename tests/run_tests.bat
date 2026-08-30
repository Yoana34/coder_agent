@echo off
rem Run all tests. PYTHONNOUSERSITE avoids user-site packages leaking into the conda env.
set PYTHONNOUSERSITE=1
cd /d "%~dp0.."
python -m pytest tests\ -v
