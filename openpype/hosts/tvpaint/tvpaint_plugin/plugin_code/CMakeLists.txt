cmake_minimum_required(VERSION 3.17)
project(OpenPypePlugin C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_EXTENSIONS OFF)

set(IP_ENABLE_UNICODE OFF)
set(IP_ENABLE_DOCTEST OFF)

if(MSVC)
    set(CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS ON)
    add_definitions(-D_CRT_SECURE_NO_WARNINGS)
endif()

# TODO better options
option(BOOST_ROOT "Path to root of Boost" "")

option(OPENSSL_INCLUDE "OpenSSL  include path" "")
option(OPENSSL_LIB_DIR "OpenSSL lib path" "")

option(WEBSOCKETPP_INCLUDE "Websocketpp include path" "")
option(WEBSOCKETPP_LIB_DIR "Websocketpp lib path" "")

option(JSONRPCPP_INCLUDE "Jsonrpcpp include path" "")

find_package(Boost 1.72.0 COMPONENTS random)

include_directories(
        "${TVPAINT_SDK_INCLUDE}"
        "${OPENSSL_INCLUDE}"
        "${WEBSOCKETPP_INCLUDE}"
        "${JSONRPCPP_INCLUDE}"
        "${Boost_INCLUDE_DIR}"
)
link_directories(
        "${OPENSSL_LIB_DIR}"
        "${WEBSOCKETPP_LIB_DIR}"
)

add_library(jsonrpcpp INTERFACE)

add_library(${PROJECT_NAME} SHARED library.cpp library.def "${TVPAINT_SDK_LIB}/dllx.c")

target_link_libraries(${PROJECT_NAME} ${Boost_LIBRARIES})
target_link_libraries(${PROJECT_NAME} jsonrpcpp)
