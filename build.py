"""직접 빌드 스크립트 — vcvarsall 환경 설정 후 cl/link 실행"""
import subprocess
import sys
import os
from pathlib import Path

SRC = Path(__file__).parent
OUT = SRC / "build"
OUT.mkdir(exist_ok=True)

VCVARS = r"C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat"

def get_msvc_env():
    cmd = f'"{VCVARS}" x64 >nul 2>&1 && set'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    env = {}
    for line in result.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            env[k] = v
    return env

def compile_source(src, obj, index, total, env):
    print(f"[{index}/{total}] {src}")
    src_path = str(SRC / src)
    obj_path = str(OUT / obj)
    inc_path = str(SRC)
    cmd = f'cl /nologo /std:c++17 /EHsc /utf-8 /c /I"{inc_path}" "{src_path}" /Fo"{obj_path}"'
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, shell=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        print(f"COMPILE FAILED: {src}")
        sys.exit(1)

def link_exe(exe_name, obj_names, env):
    print(f"[LINK] {exe_name}")
    exe_path = str(OUT / exe_name)
    obj_list = " ".join(f'"{OUT / obj}"' for obj in obj_names)
    cmd = f'link /nologo /OUT:"{exe_path}" {obj_list} ws2_32.lib'
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, shell=True)
    print(r.stdout.strip())
    if r.returncode != 0:
        print(r.stderr)
        print(f"LINK FAILED: {exe_name}")
        sys.exit(1)
    return exe_path

print("Setting up MSVC environment...")
env = get_msvc_env()
if 'INCLUDE' not in env:
    print("ERROR: vcvarsall.bat failed")
    sys.exit(1)
print("OK")

# ━━━ 공용 소스 (두 서버가 공유) ━━━
shared_sources = [
    ("Core\\World.cpp", "World.obj"),
    ("NetworkEngine\\IOCPServer.cpp", "IOCPServer.obj"),
    ("NetworkEngine\\Session.cpp", "Session.obj"),
    ("Systems\\NetworkSystem.cpp", "NetworkSystem.obj"),
    ("Systems\\MessageDispatchSystem.cpp", "MessageDispatchSystem.obj"),
]

# ━━━ FieldServer 전용 소스 ━━━
field_sources = [
    ("Systems\\InterestSystem.cpp", "InterestSystem.obj"),
    ("Systems\\BroadcastSystem.cpp", "BroadcastSystem.obj"),
    ("Systems\\GhostSystem.cpp", "GhostSystem.obj"),
    ("Servers\\FieldServer\\main.cpp", "field_main.obj"),
]

# ━━━ GateServer 전용 소스 ━━━
gate_sources = [
    ("Servers\\GateServer\\main.cpp", "gate_main.obj"),
]

all_sources = shared_sources + field_sources + gate_sources
total = len(all_sources)

for i, (src, obj) in enumerate(all_sources, 1):
    compile_source(src, obj, i, total, env)

# ━━━ 링크: FieldServer.exe ━━━
shared_objs = [obj for _, obj in shared_sources]
field_objs = shared_objs + [obj for _, obj in field_sources]
field_exe = link_exe("FieldServer.exe", field_objs, env)

# ━━━ 링크: GateServer.exe ━━━
gate_objs = shared_objs + [obj for _, obj in gate_sources]
gate_exe = link_exe("GateServer.exe", gate_objs, env)

print()
print(f"BUILD SUCCESS: {field_exe}")
print(f"BUILD SUCCESS: {gate_exe}")
