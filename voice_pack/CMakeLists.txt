cmake_minimum_required(VERSION 3.15)

project(HelixTest LANGUAGES C)

set(CMAKE_C_STANDARD 11)

# Include ../Middlewares/helix
include_directories(../Middlewares/helix)

# Add every source file in ../Middlewares/helix
file(GLOB_RECURSE SOURCES ../Middlewares/helix/*.c)

# Add the main.c file
list(APPEND SOURCES main.c)

# Create the executable
add_executable(HelixTest ${SOURCES})
