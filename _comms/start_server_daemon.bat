@echo off
title [Server Agent Daemon] ECS Game Server
echo ============================================
echo   Server Agent Daemon
echo   30초 간격으로 클라 메시지 폴링
echo   Ctrl+C로 종료
echo ============================================
echo.

cd /d "%~dp0.."
python _comms/agent_daemon.py --role server

pause
