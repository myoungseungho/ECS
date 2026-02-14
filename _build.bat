@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" x64 >nul 2>&1

set SRC=%~dp0
set OUT=%SRC%build
if not exist "%OUT%" mkdir "%OUT%"

echo [1/5] Core\World.cpp
cl /nologo /std:c++17 /EHsc /O2 /c /I"%SRC%" "%SRC%Core\World.cpp" /Fo"%OUT%\World.obj"
if errorlevel 1 (echo FAIL: World.cpp & exit /b 1)

echo [2/5] NetworkEngine\IOCPServer.cpp
cl /nologo /std:c++17 /EHsc /O2 /c /I"%SRC%" "%SRC%NetworkEngine\IOCPServer.cpp" /Fo"%OUT%\IOCPServer.obj"
if errorlevel 1 (echo FAIL: IOCPServer.cpp & exit /b 1)

echo [3/5] NetworkEngine\Session.cpp
cl /nologo /std:c++17 /EHsc /O2 /c /I"%SRC%" "%SRC%NetworkEngine\Session.cpp" /Fo"%OUT%\Session.obj"
if errorlevel 1 (echo FAIL: Session.cpp & exit /b 1)

echo [4/5] Systems\NetworkSystem.cpp
cl /nologo /std:c++17 /EHsc /O2 /c /I"%SRC%" "%SRC%Systems\NetworkSystem.cpp" /Fo"%OUT%\NetworkSystem.obj"
if errorlevel 1 (echo FAIL: NetworkSystem.cpp & exit /b 1)

echo [5/5] Servers\FieldServer\main.cpp
cl /nologo /std:c++17 /EHsc /O2 /c /I"%SRC%" "%SRC%Servers\FieldServer\main.cpp" /Fo"%OUT%\main.obj"
if errorlevel 1 (echo FAIL: main.cpp & exit /b 1)

echo [LINK] FieldServer.exe
link /nologo /OUT:"%OUT%\FieldServer.exe" "%OUT%\World.obj" "%OUT%\IOCPServer.obj" "%OUT%\Session.obj" "%OUT%\NetworkSystem.obj" "%OUT%\main.obj" ws2_32.lib
if errorlevel 1 (echo FAIL: link & exit /b 1)

echo.
echo === BUILD SUCCESS ===
