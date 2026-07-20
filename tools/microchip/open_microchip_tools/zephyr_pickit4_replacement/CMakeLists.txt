cmake_minimum_required(VERSION 3.20.0)

find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
find_package(Python3 REQUIRED COMPONENTS Interpreter)

project(zephyr_pickit4_replacement)

set(RI4_GENERATED_DIR ${CMAKE_CURRENT_BINARY_DIR}/generated)
set(RI4_GENERATED_HEADER ${RI4_GENERATED_DIR}/ri4_family_catalog_data.h)

add_custom_command(
  OUTPUT ${RI4_GENERATED_HEADER}
  COMMAND ${CMAKE_COMMAND} -E make_directory ${RI4_GENERATED_DIR}
  COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/tools/gen_ri4_catalog.py --format header --output ${RI4_GENERATED_HEADER}
  DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/tools/gen_ri4_catalog.py
    ${CMAKE_CURRENT_SOURCE_DIR}/../mchp_ri4/family_profiles.py
    ${CMAKE_CURRENT_SOURCE_DIR}/../mchp_ri4/java_knowledge.py
  WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/..
  VERBATIM
)

add_custom_target(ri4_family_catalog DEPENDS ${RI4_GENERATED_HEADER})
add_dependencies(app ri4_family_catalog)

target_sources(app PRIVATE
  src/main.c
  src/device_state.c
  src/pk4_recovered_project.c
  src/ri4_protocol.c
  src/script_dispatch.c
  src/usb_transport.c
)

target_include_directories(app PRIVATE
  ${CMAKE_CURRENT_SOURCE_DIR}/src
  ${RI4_GENERATED_DIR}
)