# IBus Google 拼音

基于 libgooglepinyin 的 Python 3 IBus 引擎。设置面板参考
`ibus-libpinyin/setup/ibus-libpinyin-preferences.ui` 的布局与 GSettings 配置设计，使用 GTK 3，
保留 Google 解码器，不需要 libpinyin。

## 构建与运行

依赖：Python 3、PyGObject、GTK 3、IBus 1.0 introspection、libgooglepinyin
及系统词典、GLib 开发工具、CMake、GNU gettext 工具（msgfmt）。繁体转换还需要 OpenCC 和 `s2t.json`。

```sh
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build
sudo cmake --install build
```

安装时编译 GSettings schema。打包时支持 `DESTDIR`；分发包应按发行版惯例
在安装/卸载后更新 schema 缓存。支持自定义安装前缀。
启动器安装到 `CMAKE_INSTALL_LIBEXECDIR`（默认 `libexec`）；RPM 构建可传入
`-DCMAKE_INSTALL_LIBEXECDIR:PATH=%{_libexecdir}`，该值会写入 `CMakeCache.txt`。

发布源码包请使用以下命令，不要直接归档含有构建目录的工作区：

```sh
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build --target package_source
```

生成的 `build/ibus-googlepinyin-0.2.0.tar.gz` 会排除 CMake 缓存、构建目录、
Python 缓存和本机隐藏目录。`.gitignore` 只影响 Git，不会影响普通 `tar`。
如果 RPM 使用旧源码包，请先更换源码包；临时修复也可以在 spec 的 `%prep`
解压后删除包内的 `build` 目录，再执行 `%build`。


从 IBus 的输入法首选项、输入法菜单的“首选项”，或
`/usr/libexec/ibus-setup-googlepinyin` 打开面板（路径由 `CMAKE_INSTALL_LIBEXECDIR` 决定）。开发目录可运行 `python3 setup.py`，
但须先执行上述 CMake 配置步骤（默认 `build` 目录）。配置通过 GSettings
持久保存，运行中的引擎即时应用变化，切换拼音设置会清空当前预编辑。

## 功能与限制

- 常规：初始中英文、全半角、简繁体；候选词方向、1–9 个候选词、
  候选词或拼音预编辑；词频/长词/短词排序。
- 拼音：全拼、自然码/微软拼音/智能ABC/紫光拼音/拼音加加/小鹤双拼、简拼、原始双拼显示、Shift 选第二候选词、
  三组可选翻页键、唯一候选自动提交、按项控制拼音纠错。
- 模糊音：十组可选声韵母替换；利用 Google 音节边界展开，最多搜索
  64 种拼写，每种最多取 200 个候选，避免组合爆炸。
- 快捷键：五类动作，可编辑 GTK accelerator 字符串、禁用和恢复默认；
  支持单独按下并释放 Shift 切换中英文。编辑后按 Enter 或移出输入框保存；
  无效和重复组合会显示警告且不保存。
- 用户数据：退出 IBus 后备份、恢复二进制用户词典；恢复前保留 `.bak`。
- 关于：项目、版本、许可证和参考项目署名。

Google 解码器自动学习与调整词频，但公开 API 没有分别禁用它们的开关，
因此面板移除了这两项开关、词典页和键盘布局选项。
文本词库导入和词库选择尚未实现。键盘布局跟随系统/IBus。简繁转换在缺少 OpenCC 时不启用。
纠错与模糊音属于上层拼写适配，结果可能与 libpinyin 不同。
多个输入上下文仍共享 libgooglepinyin 的进程级解码器。

## 验证

```sh
GSETTINGS_BACKEND=memory /usr/bin/python3 -m unittest discover -s tests -v
```

有显示器时可执行 `GSETTINGS_BACKEND=memory dbus-run-session -- /usr/bin/python3 tests/check_integration.py`
检查全部页面、按键提交、快捷键和设置即时生效。

测试使用临时用户词典，不改变用户学习数据。GTK/IBus 集成检查需要可用显示器
和独立 D-Bus 会话。不要在个人会话设置 `GSETTINGS_BACKEND=memory` 后启动日常输入法，
因为该模式不会持久保存设置。

## 双拼键位参考

六种方案的配置编号保持稳定：0 自然码、1 微软拼音、2 智能ABC、3 紫光拼音、
4 拼音加加、5 小鹤。微软与紫光的分号键可输入 ing；零声母规则按方案分别处理。
键位数据核对 [libpinyin 双拼表](https://github.com/libpinyin/libpinyin/blob/master/src/storage/double_pinyin_table.h)
与本机安装的 [Rime 小鹤方案](https://github.com/rime/rime-double-pinyin/blob/master/double_pinyin_flypy.schema.yaml)。
自然码继续使用原配置编号 0，不改变已有用户的方案选择。

IBus 下拉菜单依次显示当前语言、字母全半角、标点全半角、简繁体和首选项。
点击对应菜单项即可切换，快捷键同步更新菜单文字；切换语言会清空当前预编辑。
简繁体菜单在 OpenCC 可用时显示。菜单内的切换作用于当前引擎状态，
启动默认值仍由首选项中的“初始状态”决定。

## 界面翻译

程序使用英文源字符串，翻译位于 `po/`，采用与 ibus-libpinyin 相同的 GNU gettext
工作流。已提供简体中文（zh_CN）和繁体中文（zh_TW）；其他语言回退到英文。
`cmake --build build` 会编译 `.mo` 文件，安装到 `CMAKE_INSTALL_LOCALEDIR`，
桌面入口的译名也从 PO 文件生成。设置面板和 IBus 菜单共用同一个翻译域。

可用 `LANGUAGE=zh_TW python3 setup.py` 或 `LANGUAGE=en python3 setup.py`
预览不同语言。更新模板、新增语言与非默认构建目录的使用方法见 `po/README.md`。

双拼模式关闭“显示双拼原始输入”时，候选窗提示显示展开后的完整拼音
（例如自然码 `nihk` 显示为 `ni'hao`）；启用时显示键盘编码。
切换此选项与预编辑显示风格会即时刷新，不清空当前输入。
共用韵母键的展开按 Google 词典验证单音节，避免把 `mo` 错解为 `mu + o`，
也避免将 `ld` 的无效组合解成 `lu + ang`。`nüe/lüe` 使用 Google 接受的
`nue/lue` 拼写查询。六种方案的回归检查覆盖了词典可识别音节及零声母键位。
