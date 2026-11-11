# ETF 社区评论草稿 · v2

用于中文 ETF 社区评论的独立写作 skill。先明确本轮产品角色、阅读可用的讨论前文与合格案例，再组合正文、产品提及和素材。默认六类各四条，用户指定的数量、类别、语言与格式优先。

本仓库是单独维护的改进版，可与 [基础版](https://github.com/raymondhuang1994/etf-comment-skills) 同时安装、同题对比。没有 Dify 依赖，也没有自动发布功能。

| | 基础版 | 本版 |
| --- | --- | --- |
| 调用名称 | `$etf-comment-drafts` | `$etf-comment-drafts-v2` |
| 公开风格参考 | 简短规则与合成示例 | 短评写法对照、单条表达与整批重复检查 |
| 产品角色 | 本轮文字要求 | 区分主推、自家其他产品与外部比较对象，避免贬损自家产品 |
| 讨论与素材 | 评论正文为主 | 相关讨论区、接话位置、正文、蓝链及素材一起考虑 |
| 私有案例 | 当前任务提供 | 合格案例可保留原声和组合关系；文章、短评论与素材记录分开选取 |
| 反馈 | 当前会话为主 | 区分合格、偏好和评测划分，不把合格当作最喜欢 |
| 检验 | 格式与行为检查 | 产品立场、前文依赖、素材搭配、隐私边界与同题对照 |

这里的改进是可检查的设计变化；是否更符合某位使用者的口味，需要其实际选择和修改来验证。

## 安装与使用

```bash
git clone https://github.com/raymondhuang1994/etf-comment-skills-v2.git
cd etf-comment-skills-v2
python3 scripts/install.py
```

也可从 [Releases](https://github.com/raymondhuang1994/etf-comment-skills-v2/releases/latest) 下载 `etf-comment-drafts-v2.zip`，把其中同名目录放入支持 skill 的应用指定目录。

安装脚本使用 `$CODEX_HOME/skills`，未设置时为 `~/.codex/skills`。不会覆盖已有目录，也不会修改基础版。另一个应用可用 `--dest /path/to/skills` 指定目录。脚本需要 Python 3.9+。

更新已有安装时，先备份旧版到 skills 目录外，再用新版目录替换；私有库继续保留在独立的 `private/` 目录，不要放入安装包。若旧版有个人修改，先比较并保留这些修改。

```text
用 $etf-comment-drafts-v2 写评论草稿。
产品：虚构 ETF-A，跟踪广泛市场指数。
没有原帖。按默认分类和数量，语气直接一点。
```

信息不够写事件时，改成产品机制讨论；没有原帖也能写独立成立的评论。用户只要某一类或三条粤语时，会覆盖默认的二十四条。

需要讨论区和素材建议时，可以直接说：

```text
用 $etf-comment-drafts-v2 做一组讨论区建议和评论草稿。
主推：虚构 ETF-A；ETF-B 也是我们的产品，不能贬低。
平台和前文：使用我提供的材料。
说明适合接哪个问题、怎样引入 A，以及是否需要产品蓝链或图片。
没有读到具体帖子时，只列候选讨论方向，不假设已看过帖子。
```

纯文案任务直接交付草稿；策划任务增加讨论位置、引入理由与素材建议。产品可以由文字、原生提及或图片交代，不要求每条都报完整名称，也不按固定比例轮换格式。日 K、分时行情卡、产品页面和派息通知是不同素材；没有实际素材时只给需求，不生成虚假行情图或交易凭证。

读取当前讨论和最新资料需要宿主提供相应工具与访问权限。本 skill 不内置平台登录、帖子抓取或发布接口；访问不到时会区分候选建议与实际已读内容。

## 私有参考库

公开仓库和安装包只包含通用方法、新写的合成示例及合成测试数据。原始评论、截图、客户信息、个人偏好标签和评测输出均应保存在仓库外。

选择器默认读取：

```text
~/.codex/private/etf-comment-drafts-v2/cases.jsonl
~/.codex/private/etf-comment-drafts-v2/profile.json
```

设置了 `CODEX_HOME` 时使用该目录下的对应 `private/` 路径；可用 `ETF_COMMENT_LIBRARY` 或 `--library` 指定其他 JSONL 文件。字段与操作见 [私有参考库说明](skills/etf-comment-drafts-v2/references/private-library.md)。

用户明确认可为合格的私有案例，可以向生成环节返回原文 `reference_text` 和必要的讨论、提及与素材信息；这些仍是私有参考。旧格式或未经认可的记录继续只使用 `style_text`，不会自动退回原文。默认选择短评论，长文章和只有素材的记录不混入短评。`holdout` 永不参与选例，`disliked` 单独作为避用参考，同一表达骨架尽量只选一条。

`approval: approved` 表示用户认可为合格，`preference: liked` 表示用户另外表达过偏好，二者不能互相替代。案例里的旧数字、日期、经历和产品角色不是本轮事实；表格相邻行也不代表同一讨论串。

这是一种本地文本匹配和选例方式，不是模型微调，也不是向量检索。脚本不联网；选出的私有参考进入当前 AI 会话后，仍受该环境的数据处理设置约束。

## 怎样补充案例更有用

优先补充以下材料，无需先准备大量近似句子：

- 你喜欢或不喜欢的文案，附一句原因。
- 同一条文案的原稿与亲手修改稿。
- 不同产品、语言、讨论目的和情境的代表样本。
- 可以明确区分的产品资料、当时情境与个人表达。

新增材料按 [私有参考库说明](skills/etf-comment-drafts-v2/references/private-library.md) 整理。保留一部分样本只用于评估，不把每条都放进生成参考；不要把未给出的用户评价补成喜欢或不喜欢。

## 对照与验证

使用 [行为场景和同题对照方法](skills/etf-comment-drafts-v2/references/evaluation.md) 对比基础版与本版。比较提示词本身时给双方相同参考；比较整个使用流程时，记录是否一方调用了额外私有材料。

默认结果可检查类别和条数；写作质量由“直接可用／轻改可用／需要重写”和重复情况判断。没有实际用户评分时，不报告偏好胜率或宣称效果已验证。

开发检查与打包：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python scripts/validate.py
.venv/bin/python -m unittest discover -s tests -v
python3 scripts/package.py
```

验证脚本需要 PyYAML；安装、打包和私有案例选择器只用标准库。打包仅包含 Git 跟踪的 skill 文件与许可，不会捆绑外部私有参考库。源文件修改后需先暂存或提交再打包。

## License

[MIT](LICENSE)。中文表达清理参考 [Humanizer-zh](https://github.com/op7418/Humanizer-zh)；适用规则、来源与第三方许可随 skill 一起提供。
