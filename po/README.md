# Translations

The source language is English. Python messages use `_()` for immediate
translation or `N_()` for labels that are translated when displayed, as in
ibus-libpinyin. Do not translate settings keys, shortcuts, file names, pinyin
spellings, or text produced by the decoder.

`LINGUAS` lists the catalogs to build and install. Currently included:

- `zh_CN.po`: Simplified Chinese
- `zh_TW.po`: Traditional Chinese

## Build

```sh
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build
```

CMake uses GNU gettext `msgfmt --check --check-format` to produce
`build/locale/<language>/LC_MESSAGES/ibus-googlepinyin.mo`. Installation places
catalogs in `${CMAKE_INSTALL_LOCALEDIR}/<language>/LC_MESSAGES`. The generated
runtime configuration respects custom installation prefixes. The same PO
files supply the localized desktop entry names.

## Update or add a language

```sh
cmake --build build --target update-pot
msgmerge --update --backup=none po/zh_CN.po po/ibus-googlepinyin.pot
msgmerge --update --backup=none po/zh_TW.po po/ibus-googlepinyin.pot
```

`POTFILES.in` lists Python sources; the desktop template is extracted separately
by the same `update-pot` target. Use `msginit` with the POT to create a catalog
for a new language, add its locale to `LINGUAS`, translate the messages, and
configure/build again. Ordinary builds do not rewrite PO/POT files.

## Preview

```sh
LANGUAGE=zh_TW python3 setup.py
LANGUAGE=en python3 setup.py
```

Run these under a UTF-8 locale. For builds outside the default `build` directory,
set `IBUS_LOCALEDIR` to the build's `locale` directory. Untranslated languages
and missing catalogs fall back to the English source text.
