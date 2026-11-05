# 私有风格参考

需要读取持久案例或保存用户反馈时使用本说明。私有库放在公开仓库与 skill 安装目录之外。公开包只提供选择器和下面的全新合成格式示例。

## 读取

从 skill 目录运行：

```bash
python3 scripts/select_examples.py --query '产品比较 取舍 简短口语' --limit 6
python3 scripts/select_examples.py --query '机制问题' --category question --language zh-HK --limit 4
```

路径依次采用 `--library`、环境变量 `ETF_COMMENT_LIBRARY`，否则使用 `$CODEX_HOME/private/etf-comment-drafts-v2/cases.jsonl`；`CODEX_HOME` 未设置时基于 `~/.codex`。语言可省略，指定时只选匹配语言；粤语别名对应 `zh-HK`。默认选六条，最多十二条。类别 id 为 `observation`、`question`、`comparison`、`intention`、`event`、`topic`。

没有库时返回 `available: false`，正常使用公开合成示例。库存在但没有匹配正例时也应回退，不要求用户补齐可选信息。解析失败只报告字段和行号，不打印原文、来源路径或文件内容；先修复数据再使用，不把错误当成空库。

选择器只读本地文件，无网络请求、无模型调用，不修改数据。中文使用字和双字组合、英文使用词的重合度；优先相关参考，相关度相近时偏向用户明确喜欢的样本，同一 `cluster` 只选一条。它不理解语义相近词，也不是微调、向量 RAG 或内容质量评分。检索到的例子仍要按本轮语境判断是否适合。

## 案例格式

`cases.jsonl` 每行一个 JSON 对象。以下是完全合成的格式示意，不是真实用户评价：

```json
{"id":"demo-01","text":"行业甲看着挺热闹，我反而想知道它到底覆盖多少家公司。","style_text":"话题看着挺热闹，我反而想知道它到底覆盖多少家公司。","category":"question","language":"zh-CN","tags":["持仓范围","反问","一个关注点"],"preference":"unrated","split":"reference","cluster":"coverage-question","source":{"kind":"synthetic"},"notes":"表达特征由整理者描述，不代表用户喜欢。"}
```

必需字段：

| 字段 | 用途 |
| --- | --- |
| `id` | 唯一、稳定的非身份标识 |
| `category` | 六个类别 id 之一 |
| `language` | 如 `zh-CN`、`zh-HK`，按文本实际表达标注 |
| `tags` | 关注点、语气、句式等字符串数组 |
| `preference` | `unrated`、`liked` 或 `disliked`；只有明确用户反馈才能改变偏好标签 |
| `split` | `reference` 或 `holdout`；后者仅供独立评测，选择器永不返回 |
| `cluster` | 同义改写或同一表达骨架共用一个标识，避免重复参考 |

`style_text` 是能送入本轮上下文的表达参考：先去掉旧产品名、数字和身份，把亲历陈述改成不声称已发生的表达。缺少或留空时跳过该记录，**绝不回退输出原文 `text`**。

`text` 可保存原文，`source` 可保存来源位置，`notes` 可保存整理意见；这些仅留在私有库，不进入选择器输出。原文并非必需字段。整理意见、截图颜色或文章互动数不能自动变成用户喜欢／不喜欢的标签。

输出包含 `examples`、单列的少量 `avoid_examples`、`style_preferences` 和选择计数。`avoid_examples` 来自用户明确标为 `disliked` 的参考，只用于识别应避开的表达。输出不包含原文 `text`、`source`、`notes` 或机器路径。`style_text` 仍是私有材料，不要提交到公共仓库或公开评测报告。

## 偏好与反馈

同目录可放 `profile.json`：

```json
{"style_preferences":["句子短一些","允许有鲜明的个人偏好"],"feedback":[]}
```

`style_preferences` 只记录用户明确说过的偏好。`feedback` 可保存用户原话、适用场景和相关案例 id 的对象记录；脚本不把这些自由文本自动分类。用户明确喜欢或不喜欢某条案例后，再更新对应记录的 `preference`。所有记录继续留在私有目录。

选择器输出会进入当前 AI 助手的上下文；是否由云端模型处理、是否留存，取决于当前宿主及其配置。“未上传 GitHub”不等于“没有传给当前模型服务”。
