cmake_minimum_required(VERSION 3.12)
project(ibus-googlepinyin VERSION 0.42.0 LANGUAGES NONE)
set(CMAKE_INSTALL_LIBDIR lib CACHE PATH "Library directory")
include(GNUInstallDirs)
set(IBUS_GOOGLEPINYIN_PKGDATADIR ${CMAKE_INSTALL_FULL_DATADIR}/ibus-googlepinyin)
set(IBUS_GOOGLEPINYIN_VERSION ${PROJECT_VERSION})
configure_file(config.py.in config.py @ONLY)
add_subdirectory(po)
configure_file(googlepinyin.xml.in googlepinyin.xml @ONLY)
configure_file(data/ibus-setup-googlepinyin.in ibus-setup-googlepinyin @ONLY)
configure_file(data/ibus-setup-googlepinyin.desktop.in ibus-setup-googlepinyin.desktop.in @ONLY)
add_custom_command(
    OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/ibus-setup-googlepinyin.desktop
    COMMAND ${GETTEXT_MSGFMT_EXECUTABLE} --desktop
            --template=${CMAKE_CURRENT_BINARY_DIR}/ibus-setup-googlepinyin.desktop.in
            -d ${CMAKE_CURRENT_SOURCE_DIR}/po
            --output-file=${CMAKE_CURRENT_BINARY_DIR}/ibus-setup-googlepinyin.desktop
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/ibus-setup-googlepinyin.desktop.in ${TRANSLATION_PO_FILES}
    VERBATIM)
add_custom_target(translated-desktop ALL
    DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/ibus-setup-googlepinyin.desktop)
install(PROGRAMS ${CMAKE_CURRENT_BINARY_DIR}/ibus-setup-googlepinyin DESTINATION ${CMAKE_INSTALL_LIBEXECDIR})
find_program(GLIB_COMPILE_SCHEMAS glib-compile-schemas)
if(NOT GLIB_COMPILE_SCHEMAS)
  message(FATAL_ERROR "glib-compile-schemas is required")
endif()
set(SCHEMA org.freedesktop.ibus.engine.googlepinyin.gschema.xml)
file(MAKE_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/schemas)
configure_file(data/${SCHEMA} schemas/${SCHEMA} COPYONLY)
execute_process(COMMAND ${GLIB_COMPILE_SCHEMAS} --strict ${CMAKE_CURRENT_BINARY_DIR}/schemas
                RESULT_VARIABLE SCHEMA_RESULT)
if(NOT SCHEMA_RESULT EQUAL 0)
  message(FATAL_ERROR "Unable to compile GSettings schemas")
endif()
install(PROGRAMS main.py setup.py DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus-googlepinyin)
install(FILES engine.py factory.py libopencc.py googlepinyin.py settings.py pinyin.py decoder.py i18n.py
              ${CMAKE_CURRENT_BINARY_DIR}/config.py
        DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus-googlepinyin)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/googlepinyin.xml DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus/component)
install(FILES data/${SCHEMA} DESTINATION ${CMAKE_INSTALL_DATADIR}/glib-2.0/schemas)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/ibus-setup-googlepinyin.desktop DESTINATION ${CMAKE_INSTALL_DATADIR}/applications)
install(DIRECTORY icons/ DESTINATION ${CMAKE_INSTALL_DATADIR}/ibus-googlepinyin/icons)
install(CODE "execute_process(COMMAND \"${GLIB_COMPILE_SCHEMAS}\" \"\$ENV{DESTDIR}${CMAKE_INSTALL_FULL_DATADIR}/glib-2.0/schemas\")")
