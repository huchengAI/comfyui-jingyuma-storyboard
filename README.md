# ComfyUI 镜语马分镜提示词节点

将小说/剧本自动拆解为标准化分镜提示词，一键接入 ComfyUI 生图/生视频工作流。

由 [镜语马](https://shotstory.cn) 提供分镜引擎。

## ✨ 功能

- **生成分镜**：输入小说文本，输出 4 个结果
  - `image_prompts`：图像提示词（每行一个镜头）
  - `video_prompts`：视频提示词
  - `dialogues`：角色台词
  - `raw_json`：完整 JSON 数据
- **拆分镜头**：从生成结果中提取第 N 个镜头
- **刷新单镜头**：对某个镜头刷新不同描述版本（需标准版/专业版套餐）

## 📦 安装

### 方式一：Git Clone（推荐）

```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/huchengAI/comfyui-jingyuma-storyboard.git
cd comfyui-jingyuma-storyboard
pip install -r requirements.txt
```

### 方式二：手动下载

1. 下载本仓库 ZIP，解压到 `ComfyUI/custom_nodes/` 目录
2. 进入目录安装依赖：

```bash
cd ComfyUI/custom_nodes/comfyui-jingyuma-storyboard
pip install -r requirements.txt
```

3. 重启 ComfyUI

重启后，在节点菜单里搜索「镜语马」即可看到 3 个节点。

## 🔑 获取 API Key

1. 打开 https://shotstory.cn/?register=1
2. 手机号 + 短信验证码注册（约 30 秒）
3. 页面自动弹出 API Key（已复制到剪贴板）
4. 粘贴到节点的 `api_key` 输入框

**免费额度**：注册赠 100 积分，每日签到再送 300 积分。

## 🚀 快速开始

### 工作流示例文件

仓库提供两份示例，按需选择：

#### 最简示例

见 `workflows/jingyuma_storyboard_example.json`，只包含「镜语马 · 生成分镜」和「镜语马 · 拆分镜头」两个节点，用于查看节点接线方式。

#### 完整示例

见 `workflows/jingyuma_storyboard_full_example.json`，包含从分镜生成到 SDXL 出图的完整链路，并额外接了两个文本预览节点显示 `dialogues` 和 `raw_json`。

**导入方法**：ComfyUI 界面 → 拖拽 JSON 文件到画布 → 填入 API Key → 在 `CheckpointLoaderSimple` 里选好本地模型 → 点运行。

> 若提示缺少 `PreviewText` 节点，请升级 ComfyUI 到最新版，或删除这两个预览节点，不影响出图。

## 💰 计费

| 操作 | 计费 |
|------|------|
| 生成分镜 | 1 字 = 1 积分 |
| 刷新单镜头 | 按镜头原句字数计费 |
| 提交复审 | 不额外扣费 |

**免费积分**（注册赠送 + 每日签到）当天有效，次日清零。积分不足时前往 https://shotstory.cn 充值。

## 🐛 常见问题

**Q: 报错「API Key 无效」**  
A: 检查 Key 是否复制完整（无空格、无换行）。可在官网「个人中心 → API 管理」重新生成。

**Q: 报错「积分不足」**  
A: 前往 https://shotstory.cn 充值，或明天再试（免费积分每日刷新）。

**Q: 报错「文本过长」**  
A: 单次上限 10000 字，请拆分为多段分别生成。

**Q: 生成的镜头少于预期**  
A: 免费版最多 10 镜头，基础版 100，标准版 500，专业版 1000。升级套餐可解锁更多。

**Q: 输出的中文乱码**  
A: 确保 ComfyUI 的 Python 版本 ≥ 3.8，且系统 locale 支持 UTF-8。

## 📄 许可

MIT License

## 🔗 链接

- 镜语马官网：https://shotstory.cn
- 反馈问题：https://github.com/huchengAI/comfyui-jingyuma-storyboard/issues
