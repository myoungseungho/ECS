cmake_minimum_required(VERSION 3.15)
project(GameServerSkeleton LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Windows 소켓 라이브러리
if(WIN32)
    link_libraries(ws2_32)
endif()

# ━━━ Core (ECS) ━━━
add_library(Core STATIC
    Core/World.cpp
)
target_include_directories(Core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# ━━━ NetworkEngine (IOCP) ━━━
add_library(NetworkEngine STATIC
    NetworkEngine/IOCPServer.cpp
    NetworkEngine/Session.cpp
)
target_include_directories(NetworkEngine PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})

# ━━━ Systems ━━━
add_library(Systems STATIC
    Systems/NetworkSystem.cpp
)
target_include_directories(Systems PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
target_link_libraries(Systems PUBLIC Core NetworkEngine)

# ━━━ Field Server (실행 파일) ━━━
add_executable(FieldServer
    Servers/FieldServer/main.cpp
)
target_link_libraries(FieldServer PRIVATE Systems Core NetworkEngine)
