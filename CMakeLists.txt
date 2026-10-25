cmake_minimum_required(VERSION 3.12)
project(ibus-googlepinyin LANGUAGES NONE)

set(IBUS_PREFIX /usr)
set(IBUS_GOOGLEPINYIN_PKGDATADIR ${IBUS_PREFIX}/share/ibus-googlepinyin)
set(IBUS_GOOGLEPINYIN_VERSION 0.2.0)

configure_file(googlepinyin.xml.in ${CMAKE_CURRENT_BINARY_DIR}/googlepinyin.xml)

install(PROGRAMS main.py       DESTINATION ${IBUS_PREFIX}/share/ibus-googlepinyin)
install(FILES engine.py factory.py libopencc.py googlepinyin.py DESTINATION ${IBUS_PREFIX}/share/ibus-googlepinyin)
install(FILES ${CMAKE_CURRENT_BINARY_DIR}/googlepinyin.xml DESTINATION ${IBUS_PREFIX}/share/ibus/component/)
install(DIRECTORY icons/       DESTINATION ${IBUS_PREFIX}/share/ibus-googlepinyin/icons)

