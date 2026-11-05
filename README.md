# ETF 社区评论草稿 · v2

用于中文 ETF 社区评论的独立写作 skill。先选择具体关注点，再写候选、筛选和分组；默认六类各四条，用户指定的数量、类别、语言与格式优先。

本仓库是单独维护的改进版，可与 [基础版](https://github.com/raymondhuang1994/etf-comment-skills) 同时安装、同题对比。没有 Dify 依赖，也没有自动发布功能。

| | 基础版 | 本版 |
| --- | --- | --- |
| 调用名称 | `$etf-comment-drafts` | `$etf-comment-drafts-v2` |
| 公开风格参考 | 简短规则与合成示例 | 12 组写法对照与候选筛选方法 |
| 私有案例 | 当前任务提供 | 可从仓库外私有库选择参考，缺库时继续使用公开示例 |
| 反馈 | 当前会话为主 | 显式偏好记录、喜欢／不喜欢分开使用 |
| 检验 | 格式与行为检查 | 保留行为检查，并提供同题盲评方法 |

这里的改进是可检查的设计变化；是否更符合某位使用者的口味，需要其实际选择和修改来验证。

## 安装与使用

```bash
git clone https://github.com/raymondhuang1994/etf-comment-skills-v2.git
cd etf-comment-skills-v2
python3 scripts/install.py
```

也可从 [Releases](https://github.com/raymondhuang1994/etf-comment-skills-v2/releases/latest) 下载 `etf-comment-drafts-v2.zip`，把其中同名目录放入支持 skill 的应用指定目录。

安装脚本使用 `$CODEX_HOME/skills`，未设置时为 `~/.codex/skills`。不会覆盖已有目录，也不会修改基础版。另一个应用可用 `--dest /path/to/skills` 指定目录。脚本需要 Python 3.9+。

```text
用 $etf-comment-drafts-v2 写评论草稿。
产品：虚构 ETF-A，跟踪广泛市场指数。
没有原帖。按默认分类和数量，语气直接一点。
```

信息不够写事件时，改成产品机制讨论；没有原帖也能写独立成立的评论。用户只要某一类或三条粤语时，会覆盖默认的二十四条。

## 私有参考库

公开仓库和安装包只包含通用方法、新写的合成示例及合成测试数据。原始评论、截图、客户信息、个人偏好标签和评测输出均应保存在仓库外。

选择器默认读取：

```text
~/.codex/private/etf-comment-drafts-v2/cases.jsonl
~/.codex/private/etf-comment-drafts-v2/profile.json
```

设置了 `CODEX_HOME` 时使用该目录下的对应 `private/` 路径；可用 `ETF_COMMENT_LIBRARY` 或 `--library` 指定其他 JSONL 文件。字段与操作见 [私有参考库说明](skills/etf-comment-drafts-v2/references/private-library.md)。

选择器只向生成环节返回处理后的 `style_text`、类别与明确偏好等必要字段，不返回原文 `text` 或来源信息。`holdout` 样本不参与选例；`disliked` 单独作为避用参考；同一表达骨架尽量只选一条。尚未评分的样本不会被当成用户已经认可。

这是一种本地文本匹配和选例方式，不是模型微调，也不是向量检索。脚本不联网；选出的私有参考进入当前 AI 会话后，仍受该环境的数据处理设置约束。

## 怎样补充案例更有用

优先补充以下材料，无需先准备大量近似句子：

- 你喜欢或不喜欢的文案，附一句原因。
- 同一条文案的原稿与亲手修改稿。
- 不同产品、语言、讨论目的和情境的代表样本。
- 可以明确区分的产品资料、当时情境与个人表达。

新增材料按 [私有参考库说明](skills/etf-comment-drafts-v2/references/private-library.md) 整理。保留一部分样本只用于评估，不把每条都放进生成参考；不要把未给出的用户评价补成喜欢或不喜欢。

## 对照与验证

使用 [三个固定场景和盲评方法](skills/etf-comment-drafts-v2/references/evaluation.md) 对比基础版与本版。比较提示词本身时给双方相同参考；比较整个使用流程时，记录是否一方调用了额外私有材料。

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

[MIT](LICENSE)
