# 私有案例与讨论语境

私有库放在公开仓库与 skill 安装目录之外。原文、整理后的表达、图片、评论链接、用户反馈和评测结果都属于私有材料；公开包只保留通用方法与全新合成示例。用户确认整份材料合格时，可以批量标记合格，无需逐条索取评分；“合格”不等于“最喜欢”或“有传播效果”。

## 先取文字，再按需看素材

从 skill 目录运行：

```bash
python3 scripts/select_examples.py --query '行业讨论 产品引入' --limit 6
python3 scripts/select_examples.py --query '跟着前文追问' --platform '平台甲' --speech-act question
python3 scripts/select_examples.py --query '图中产品' --include-media --limit 3
python3 scripts/select_examples.py --query '产品机制' --content-type article
```

路径依次采用 `--library`、环境变量 `ETF_COMMENT_LIBRARY`，否则使用 `$CODEX_HOME/private/etf-comment-drafts-v2/cases.jsonl`；`CODEX_HOME` 未设置时基于 `~/.codex`。同目录的 `profile.json` 提供用户明确的风格偏好。

- 默认 `--content-type comment`，不混入长文章或只有图片的记录。`article` 只选文章；`all` 放开类型筛选，但无可用文字的记录仍不作为语言参考。
- `--category` 与 `--language` 是硬筛选。类别 id 仍为 `observation`、`question`、`comparison`、`intention`、`event`、`topic`；`粤语` 等语言别名对应 `zh-HK`。
- `--platform`、`--speech-act` 是排序偏好，不会因平台或动作不完全相同而把候选池清空。动作字段可用 `question`、`reaction`、`reply`、`share`、`explain` 等自定标签，不限制成新的固定文案分类。
- `--limit` 默认六条，范围一至十二。先用相关的产品机制、讨论主题和接话动作查询，再判断这些参考是否适合本轮。
- 默认只返回素材的类型、单元格、说明与已检查状态。需要看原图时再加 `--include-media` 取得私有路径；脚本本身不打开图片、不 OCR、不联网、不改文件。只看本轮相关图片，未看过的图片不能当作已理解。

选择器使用中文字符和双字组合、英文词的重合度，相关程度相近时参考合格状态、明确偏好、平台和动作；同一 `cluster` 只选一条。任何字词匹配优先于完全无匹配。它不是语义检索、微调或写作效果评分，不懂完整产品关系；模型仍需读上下文判断。

缺库时返回 `available: false`，用会话参考或公开合成示例继续。库存在但无合适正例时也应回退。解析失败只报告行号和字段，不打印原文、字段值或机器路径；不要把解析错误当成正常空库。

## 原文授权与旧库兼容

每条记录沿用必需字段：`id`、`category`、`language`、`tags`（字符串数组）、`preference`、`split`、`cluster`。另有以下可选字段：

| 字段 | 用途与默认值 |
| --- | --- |
| `approval` | `approved` 表示用户已明确认可此材料可作为参考；默认 `unreviewed`。不能根据截图颜色、点赞或整理者评分自动认可 |
| `content_type` | `comment`、`article`、`asset_only`；旧记录默认 `comment` |
| `text` | 私有原文；`approved` 且非空时以 `reference_text` 返回，保留原本句长、停顿和表达 |
| `style_text` | 旧库处理过的表达。未获原文参考认可时仍只用此字段，绝不自动回退到 `text`；已认可但没有原文时也可使用 |
| `platform`、`speech_act` | 平台和这句话的动作，帮助选择相似场景 |
| `context` | 已记录的讨论位置、产品提及和前文信息，见下节 |
| `media` | 图片或卡片与记录的对应关系，见下节 |
| `source` | 私有来源记录；选择结果仅可返回工作表名及行号，不输出完整来源对象、评论 URL 或原文件路径 |
| `notes` | 整理备注，留在私有库，不进入选例输出 |

`preference` 仍为 `unrated`、`liked`、`disliked`；只有用户明确的偏好反馈才改变它。`approved + unrated` 是正常组合。`split=holdout` 无论是否合格都不参与生成参考；若旧库把同一 `cluster` 的其他记录标为 `reference`，这些记录也一并排除，分别计入 `excluded_holdout` 与 `excluded_holdout_cluster`，避免同一表达骨架进入生成与评测两边。`disliked` 单列为最多两条避用参考，不能混入正例。

未认可的旧记录只输出 `style_text` 和基本标签，不输出新增语境、素材或平台动作字段。缺少可用文字的记录被跳过并计数。

## 留住组合关系，不补造讨论前文

`context` 可包含以下字符串字段：

- `discussion_area`：原记录所在的标的区、帖子或话题。
- `link_target`：蓝链指向什么；空白不等于页面没有任何蓝链，截图可能另有讨论区标的链接。
- `requirements`、`media_note`：原记录的要求与配图说明。
- `preceding_text`：确实取得的原帖或前面评论，缺少时省略，不能从相邻记录编造。
- `context_status`：例如 `not_read`、`partial`、`provided`，说明前文覆盖程度；不要把存在链接当成已经读取。
- `primary_product`：原任务明确的主推产品；无法确定时省略。
- `source_date`：案例当时的日期，便于区分历史情境。

`own_products` 是字符串数组，只记录有明确归属依据的自家产品。历史任务的主推与比较角色不是本轮角色；同一代码曾是讨论区标的不代表它永远是竞品。不能仅凭讨论区或蓝链字段推断完整归属。

`media` 是对象数组，可用字段 `kind`、`path`、`cell`、`description`（字符串）与 `verified`（布尔值）。`kind` 可区分日 K、分时行情卡、产品页面、派息通知、测算页面或未检查图片。无法辨认时保留未检查状态，不统称日 K。

**原文进入模型上下文是为了学表达与组合，不把旧数字、旧事件、交易经历和立场移入新评论。** 参考中“这只”“图里”“楼主”等表达，只有本轮确有对应产品、图片或前文才可沿用。原记录属于短评论、图注、转发语还是文章，也要分别理解。

下面是完全新写的格式示例，其中的平台、产品和文本均为虚构：

```json
{"id":"demo-01","text":"这张图里哪一部分是本次新加的？","category":"question","language":"zh-CN","tags":["看图追问"],"approval":"approved","preference":"unrated","split":"reference","cluster":"image-followup","content_type":"comment","platform":"平台甲","speech_act":"question","context":{"discussion_area":"虚构行业话题","context_status":"partial","media_note":"问题依赖配图，未提供完整原帖"},"media":[{"kind":"product_page","cell":"H2","description":"合成产品构成示意","verified":false}],"source":{"sheet":"合成示例","row":2}}
```

## 保存明确反馈

`profile.json` 的 `style_preferences` 仅记录用户明确表达的要求，`feedback` 可保存用户原话、适用场景及相关案例 id 的对象记录；脚本不会从自由文本推断“喜欢”标签。

```json
{"style_preferences":["不要把自家产品写成嫌弃的对象","每条保留一个具体关注点"],"feedback":[]}
```

输出的 `reference_text`、`context`、`media`、`source_location` 与 `style_text` 都可能是私有内容，不得放入公开测试、日志、截图演示或发布包。脚本不联网；选例进入当前 AI 会话后，仍受宿主及其模型服务的数据处理设置约束，“未上传 GitHub”不等于“未传给模型服务”。
