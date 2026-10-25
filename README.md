# IBus Google 拼音

基于 libgooglepinyin 的 Python 3 IBus 引擎。设置面板参考
`ibus-libpinyin/setup/ibus-libpinyin-preferences.ui` 的布局与 GSettings 配置设计，使用 GTK 3，

## 构建与运行

依赖：Python 3、PyGObject、GTK 3、IBus 1.0 introspection、libgooglepinyin
及系统词典、GLib 开发工具、CMake、GNU gettext 工具（msgfmt）。繁体转换还需要 OpenCC 和 `s2t.json`。

```sh
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=/usr
cmake --build build
sudo cmake --install build
```

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
