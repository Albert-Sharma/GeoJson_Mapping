@echo off
cd /d "%~dp0"
C:\Python314\python.exe -m streamlit run district_map_webapp.py --server.address 0.0.0.0 --server.port 8501
