# 桌面备忘录

一个基于 Python Tkinter 的 Windows 桌面备忘录小组件。

## 功能

- 莫兰迪配色界面
- 多条便签的新建、编辑、删除和搜索
- Markdown 编辑与预览，支持标题、列表、加粗、行内代码和代码块
- 便签置顶，置顶便签会排在列表前面并在悬浮窗显示图钉标记
- 自动保存本地便签内容
- 可拖拽调整“便签列表”和“编辑内容”的宽度
- 独立的桌面悬浮便签小组件
- 悬浮窗可拖动，显示当前便签内容
- 窗口位置、大小和分栏宽度自动记忆
- 使用 `pythonw.exe` 启动，不显示终端窗口

## 启动方式

直接双击桌面上的“桌面备忘录”快捷方式，打开完整编辑窗口。

双击“桌面悬浮便签”快捷方式，只打开桌面悬浮小组件；点击小组件中的“打开编辑”才打开完整编辑窗口。

也可以直接运行：

```text
outputs\\DesktopMemo.py
```

仅启动悬浮窗：

```text
outputs\\DesktopMemo.py --widget-only
```

电脑需要安装 Python 3，并包含 Tkinter。便签数据默认保存在 Windows 用户目录的 `AppData\\Roaming\\DesktopMemo\\notes.json`。

## 项目文件

- `outputs/DesktopMemo.py`：主程序和悬浮窗程序
- `outputs/DesktopMemo.exe`：无需安装 Python 的 Windows 可执行文件
- `outputs/desktop-memo-icon.ico`：Windows 快捷方式图标
- `outputs/desktop-memo-icon.png`：图标预览
- `outputs/桌面备忘录使用说明.txt`：中文使用说明

本仓库不会提交本地 `notes.json`，避免上传个人便签内容。
