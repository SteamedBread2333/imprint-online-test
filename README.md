# imprint 在线实验（token 与准确率）

**在线报告（GitHub Pages）：** [https://steamedbread2333.github.io/imprint-online-test/](https://steamedbread2333.github.io/imprint-online-test/)

在真实 `imprint-mcp` stdio 上对照：

1. **规则记忆**：无记忆体每轮重注入规范全文 vs `add` 一次 + `find` 召回。
2. **Shelves**：**对照** 宿主默认 `rg -i` 后 Read **grep 命中的全部**文件全文；**实验** 同一 rg（名单 + 宽时 rg -n 样本）；indexed &gt; k 时 `find(paths)` + documents JSON，**grep∩find 非空则 Read 交集全部篇**，否则与对照一样 Read 全部 grep 命中。`find_top_k` 只触发 find / 限制 find 返回，**不 cap Read 篇数**。语料套话避免 rg 因页眉命中全部文件。
3. **规则关联**（`record.html`）：专用 vault `.imprint-link-bench`，`add` 时写 `sources`；三个场景对照「只 Read 文档全文」vs「find 返回 rules+documents+links，按 sources Read 金标篇」；含 `get` 规则/chunk 双向溯源。
4. **语义写闸**（`semantic.html`）：在隔离 vault 上对 [imprint-embed-sidecar](https://github.com/SteamedBread2333/imprint-embed-sidecar) 的 60 对 calibration 样本跑真实 `imprint add`（duplicate / conflict / unrelated）。**需要 sidecar `ready`**（见下）。

当前语料：16 条规范、24 轮对话、16 篇文档、36 组检索查询（含 12 组组合词）、24 组偏差查询（16 组组合词 + 8 组标识符）；语义闸另用 sidecar `samples.py` 固定 20+20+20 对。

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
# 语义写闸：同级 clone sidecar，安装 venv 并启动（imprint 主仓根目录亦可）
# git clone …/imprint-embed-sidecar ../imprint-embed-sidecar
# (cd ../imprint-embed-sidecar && ./scripts/setup.sh)
# imprint embed prepare && imprint plugin start embed   # 或设置 IMPRINT_EMBED_SIDECAR
python3 experiment/scripts/run_all.py
```

需要本机 PATH 中的 `imprint-mcp`，或设置 `IMPRINT_MCP`；语义段另需 `imprint` CLI 与 **`GET http://127.0.0.1:4174/health` → `"ready": true`**（`run_all` 会尝试 `imprint plugin start embed`）。sidecar 路径：同级 `../imprint-embed-sidecar` 或 `IMPRINT_EMBED_SIDECAR`。首次运行会从 Hugging Face 拉取 tokenizer.json（约 17 MB，缓存后离线可用）。报表与数据只写二进制文件名，不写本机绝对路径。

报表（Pages 同上链接；本地路径）：

- [index](https://steamedbread2333.github.io/imprint-online-test/) · `experiment/report/index.html`
- [report.html](https://steamedbread2333.github.io/imprint-online-test/report.html) — 规则记忆
- [retrieval.html](https://steamedbread2333.github.io/imprint-online-test/retrieval.html) — shelves
- [record.html](https://steamedbread2333.github.io/imprint-online-test/record.html) — vault ↔ 文档关联
- [semantic.html](https://steamedbread2333.github.io/imprint-online-test/semantic.html) — embed + relate 写闸

原始数据在 `experiment/data/`。