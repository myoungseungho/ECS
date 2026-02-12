@echo off
title [Client Agent Daemon] ECS Game Client
echo ============================================
echo   Client Agent Daemon
echo   30초 간격으로 서버 메시지 폴링
echo   Ctrl+C로 종료
echo ============================================
echo.

cd /d "%~dp0.."
python _comms/agent_daemon.py --role client

pause
