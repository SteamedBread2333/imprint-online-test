# imprint 在线实验（token 与准确率）

**在线报告（GitHub Pages）：** [https://steamedbread2333.github.io/imprint-online-test/](https://steamedbread2333.github.io/imprint-online-test/)

在真实 `imprint-mcp` stdio 上对照：

1. **规则记忆**：无记忆体每轮重注入规范全文 vs `add` 一次 + `find` 召回。
2. **Shelves**：**对照** 宿主默认 `rg -i` 后 Read **grep 命中的全部**文件全文；**实验** 同一 rg（名单 + 宽时 rg -n 样本）；indexed &gt; k 时 `find(paths)` + documents JSON，**grep∩find 非空则 Read 交集全部篇**，否则与对照一样 Read 全部 grep 命中。`find_top_k` 只触发 find / 限制 find 返回，**不 cap Read 篇数**。语料套话避免 rg 因页眉命中全部文件。
3. **规则关联**（`record.html`）：专用 vault `.imprint-link-bench`，`add` 时写 `sources`；三个场景对照「只 Read 文档全文」vs「find 返回 rules+documents+links，按 sources Read 金标篇」；含 `get` 规则/chunk 双向溯源。

当前语料：16 条规范、24 轮对话、16 篇文档、36 组检索查询（含 12 组组合词）、24 组偏差查询（16 组组合词 + 8 组标识符）。

## 分词器

Grok 4.6 官方词表未公开。默认使用 [alvarobartt/grok-2-tokenizer](https://huggingface.co/alvarobartt/grok-2-tokenizer)（Grok 家族已公开编码器），本地可复现，不需要 xAI API。

若有 xAI 密钥，可改用官方 tokenize API 按 grok-4.6 计 token：

```bash
export XAI_API_KEY=...
export IMPRINT_TOKENIZER=grok46   # 需要 pip install xai-sdk
python3 experiment/scripts/run_all.py
```

其它对照：

```bash
export IMPRINT_TOKENIZER=tiktoken-o200k   # GPT-4o 编码
```

## 运行

```bash
python3 -m pip install -r requirements.txt
python3 experiment/scripts/run_all.py
```

需要本机 PATH 中的 `imprint-mcp`，或设置 `IMPRINT_MCP`。首次运行会从 Hugging Face 拉取 tokenizer.json（约 17 MB，缓存后离线可用）。报表与数据只写二进制文件名，不写本机绝对路径。

报表（Pages 同上链接；本地路径）：

- [index](https://steamedbread2333.github.io/imprint-online-test/) · `experiment/report/index.html`
- [report.html](https://steamedbread2333.github.io/imprint-online-test/report.html) — 规则记忆
- [retrieval.html](https://steamedbread2333.github.io/imprint-online-test/retrieval.html) — shelves
- [record.html](https://steamedbread2333.github.io/imprint-online-test/record.html) — vault ↔ 文档关联

原始数据在 `experiment/data/`。

## GitHub Pages

推送 `main` 后，Actions 工作流 **GitHub Pages — experiment reports** 会发布 `experiment/report/`（默认使用仓库内已提交的 HTML，不重新跑实验）。

- 站点根 URL：[https://steamedbread2333.github.io/imprint-online-test/](https://steamedbread2333.github.io/imprint-online-test/)（需在仓库 **Settings → Pages → Build and deployment** 选 **GitHub Actions**）
- 要 CI 重跑实验再发布：Actions → 该工作流 → **Run workflow**，勾选 **Re-run full experiment before deploy**

本地安装 `imprint-mcp`（不进 git）：

```bash
bash experiment/scripts/install_imprint_bin.sh
export IMPRINT_MCP="$PWD/experiment/bin/imprint-mcp"
python3 experiment/scripts/run_all.py
```

## 仓库体积

当前体积主要来自 **已 git 跟踪的** `experiment/bin/` 二进制（约 140MB）与各 `.imprint*` 运行时（vault、WAL、telemetry）。`.gitignore` 已排除这些路径；若要从历史中瘦身，对已跟踪文件执行 `git rm -r --cached experiment/bin/imprint experiment/bin/imprint-mcp 'experiment/bin/*.tar.gz' .imprint* …` 后再提交（二进制改由 `install_imprint_bin.sh` 或 CI 下载）。

报表与 `experiment/data/*.json` 的 `meta.imprint_mcp` 只记录二进制**文件名**（如 `imprint-mcp`），不含本机绝对路径。
