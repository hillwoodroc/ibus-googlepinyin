find_package(Gettext REQUIRED)
set(GETTEXT_MSGFMT_EXECUTABLE ${GETTEXT_MSGFMT_EXECUTABLE} PARENT_SCOPE)
file(STRINGS ${CMAKE_CURRENT_SOURCE_DIR}/LINGUAS TRANSLATION_LANGUAGES
     REGEX "^[a-zA-Z0-9_@.-]+$")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS LINGUAS)
set(TRANSLATION_PO_FILES)
set(TRANSLATION_MO_FILES)
foreach(lang IN LISTS TRANSLATION_LANGUAGES)
    set(po_file ${CMAKE_CURRENT_SOURCE_DIR}/${lang}.po)
    set(mo_dir ${PROJECT_BINARY_DIR}/locale/${lang}/LC_MESSAGES)
    set(mo_file ${mo_dir}/${PROJECT_NAME}.mo)
    add_custom_command(OUTPUT ${mo_file}
        COMMAND ${CMAKE_COMMAND} -E make_directory ${mo_dir}
        COMMAND ${GETTEXT_MSGFMT_EXECUTABLE} --check --check-format
                --output-file=${mo_file} ${po_file}
        DEPENDS ${po_file}
        VERBATIM)
    list(APPEND TRANSLATION_PO_FILES ${po_file})
    list(APPEND TRANSLATION_MO_FILES ${mo_file})
    install(FILES ${mo_file} DESTINATION ${CMAKE_INSTALL_LOCALEDIR}/${lang}/LC_MESSAGES)
endforeach()
set(TRANSLATION_PO_FILES ${TRANSLATION_PO_FILES} PARENT_SCOPE)
add_custom_target(translations ALL DEPENDS ${TRANSLATION_MO_FILES})

# Maintainer-only target; ordinary builds never rewrite source catalogs.
find_program(XGETTEXT_EXECUTABLE xgettext)
if(XGETTEXT_EXECUTABLE)
    add_custom_target(update-pot
        COMMAND ${XGETTEXT_EXECUTABLE} --from-code=UTF-8 --keyword=_ --keyword=N_
                --add-comments=Translators --package-name=${PROJECT_NAME}
                --package-version=${PROJECT_VERSION}
                --files-from=po/POTFILES.in --output=po/${PROJECT_NAME}.pot
        COMMAND ${XGETTEXT_EXECUTABLE} --language=Desktop --from-code=UTF-8
                --package-name=${PROJECT_NAME} --package-version=${PROJECT_VERSION}
                --join-existing --output=po/${PROJECT_NAME}.pot
                data/ibus-setup-googlepinyin.desktop.in
        WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
        VERBATIM)
endif()
