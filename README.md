# Dota 2 中文→英文翻译器

在Dota2游戏中输入中文，按指定按键自动翻译为英文并发送。

## 功能特点

- ✅ **现代化GUI界面** - 告别黑窗口，美观易用
- ✅ **系统托盘支持** - 可最小化到托盘，不影响游戏
- ✅ **仅在Dota2内生效** - 自动检测Dota2窗口
- ✅ **可自定义触发键** - 支持任意按键（默认F6）
- ✅ **国内可用** - 使用MyMemory API，无需翻墙
- ✅ **本地缓存** - 相同文本秒级返回
- ✅ **实时日志** - 查看翻译历史和状态

## 快速开始

### 方式1：直接使用EXE（推荐）⭐

**适合所有用户，无需Python环境**

1. **下载EXE文件**
   - 从 [Releases](../../releases) 下载 `Dota2_Translator_GUI.exe`
   - 或自行打包：双击 `build_gui.bat`

2. **运行程序**
   ```
   双击 Dota2_Translator_GUI.exe
   ```

3. **使用界面**
   - 点击"设置触发键" → 按下你想用的键（如F7）
   - 点击"保存配置"
   - 点击"最小化到托盘"
   - 进入Dota2游戏使用

### 方式2：使用源码运行

**适合开发者**

```bash
# 安装依赖
pip install -r requirements.txt

# 运行GUI版本
python src/dota2_translator_gui.py

# 或双击 start_gui.bat
```

## 使用方法

1. 运行程序，看到图形界面
2. 点击"设置触发键"，按下你想用的键（如F7）
3. 点击"保存配置"（可选）
4. 点击"最小化到托盘"
5. 进入Dota2游戏
6. 打开聊天框（按Enter）
7. 输入中文：`帮我买眼`
8. 按 **F7** 键
9. 自动翻译并发送：`Help me buy glasses`

## 项目结构

```
dota2/
├── src/
│   └── dota2_translator_gui.py    # GUI主程序
├── dist/
│   └── Dota2_Translator_GUI.exe    # 打包好的EXE
├── config.example.json              # 配置模板
├── requirements.txt                 # Python依赖
├── start_gui.bat                    # 启动脚本
├── build_gui.bat                    # 打包脚本
├── .gitignore                       # Git忽略规则
├── EXE_USAGE.md                     # EXE使用说明
└── README.md                        # 本文档
```

## 配置说明

### 配置文件 (config.json)

首次运行会自动生成，可手动编辑：

```json
{
    "trigger_key": "f6",
    "toggle_hotkey": "ctrl+alt+t",
    "cooldown": 0.2,
    "source_lang": "zh-CN",
    "target_lang": "en"
}
```

### 支持的触发键

- **功能键**: F1-F12
- **字母键**: A-Z
- **数字键**: 0-9
- **特殊键**: space, enter, tab

## 打包成EXE

```bash
双击 build_gui.bat
```

输出文件位于 `dist/` 目录，约65MB。

## 系统要求

- Windows 7/8/10/11 (64位)
- Python 3.7+（仅源码运行需要）
- 网络连接（用于翻译API）

## 常见问题

### Q: 按触发键没反应？
- 确保Dota2窗口在前台
- 确保聊天框已打开
- 检查是否输入了中文
- 在GUI中查看状态是否为"已启动"

### Q: 如何更换触发键？
- 点击"设置触发键"按钮，直接按下你想用的键

### Q: 杀毒软件报毒？
- 这是误报，因为程序使用了键盘监听功能
- 添加到信任列表即可

### Q: 需要联网吗？
- 需要！翻译功能调用在线API
- 首次翻译可能需要1-2秒

## 技术栈

- **GUI**: Tkinter + Pystray（系统托盘）
- **翻译**: MyMemory Translation API
- **键盘监听**: keyboard
- **自动化**: pyautogui + pyperclip
- **打包**: PyInstaller

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

---

**⭐ 如果这个项目对你有帮助，请给一个Star！**
