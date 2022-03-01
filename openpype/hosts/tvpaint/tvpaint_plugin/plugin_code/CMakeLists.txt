cmake_minimum_required(VERSION 3.17)
project(OpenPypePlugin C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS OFF)

set(IP_ENABLE_UNICODE OFF)
set(IP_ENABLE_DOCTEST OFF)

if(MSVC)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
    # Define WIN64 or WIN32 for TVPaint SDK
    if(CMAKE_SIZEOF_VOID_P EQUAL 8)
        message("64bit")
        add_definitions(-DWIN64)
    elseif(CMAKE_SIZEOF_VOID_P EQUAL 4)
        message("32bit")
        add_definitions(-DWIN32)
    endif()
endif()

# TODO better options
option(BOOST_ROOT "Path to root of Boost" "")

option(OPENSSL_INCLUDE "OpenSSL include path" "")
option(OPENSSL_LIB_DIR "OpenSSL lib path" "")

option(WEBSOCKETPP_INCLUDE "Websocketpp include path" "")

option(JSONRPCPP_INCLUDE "Jsonrpcpp include path" "")

# Use static boost libraries
set(Boost_USE_STATIC_LIBS ON)

find_package(Boost COMPONENTS random chrono date_time regex REQUIRED)

include_directories(
        "${TVPAINT_SDK_INCLUDE}"
        "${OPENSSL_INCLUDE}"
        "${WEBSOCKETPP_INCLUDE}"
        "${JSONRPCPP_INCLUDE}"
        "${Boost_INCLUDE_DIRS}"
)

link_directories(
        "${OPENSSL_LIB_DIR}"
        "${Boost_LIBRARY_DIRS}"
)

add_library(jsonrpcpp INTERFACE)

add_library(${PROJECT_NAME} SHARED library.cpp library.def "${TVPAINT_SDK_LIB}/dllx.c")

target_link_libraries(${PROJECT_NAME} ${Boost_LIBRARIES})
target_link_libraries(${PROJECT_NAME} jsonrpcpp)
