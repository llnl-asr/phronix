# Lessons: software_cmake

- [L-552d8aba] find_package(dftracer CONFIG REQUIRED) fails: imported target dftracer_core references /project/build/... or brahma_DIR not found -> prerelease wheel's CMake config hardcodes the build machine's paths and requires unshipped brahma -> link -I/-L/-ldftracer_core directly or define a manual IMPORTED target (tools_dftracer) (2026-11-13)
