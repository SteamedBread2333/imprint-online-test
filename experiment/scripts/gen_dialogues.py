#!/usr/bin/env python3
"""Write experiment/dialogues.json — 8 build rounds (16 rules) + 16 comply."""
import json
import os

from paths import BASE

ROUNDS = []


def R(n, phase, user, task, scope, query, qlocal, rules):
    ROUNDS.append({
        "round": n,
        "phase": phase,
        "user_message": user,
        "task": task,
        "find_scope": scope,
        "find_query": query,
        "find_query_local": qlocal,
        "new_rules": rules,
    })


def rule(claim, scope, text, qlocal):
    return {"claim": claim, "scope": scope, "text": text, "query_local": qlocal}


R(1, "build",
  "开始搭 user 模块，同时定两条 Python 基础规范：命名风格和分层依赖。",
  "给 user_service.py 写一个骨架（类名 UserService、函数 get_user_by_id）。",
  "aurora,python", "naming architecture layers", "命名 架构 分层 依赖",
  [
      rule("Use snake_case for functions/variables and PascalCase for classes",
           "aurora,python",
           "函数和变量统一用 snake_case，类名用 PascalCase。这是从项目第一天就定的风格，跟社区 PEP8 对齐，代码 review 时一眼能分清标识符是函数、变量还是类型。公开常量用全大写 SNAKE_CASE，不要混用 camelCase。",
           "命名规范 snake_case PascalCase 函数 变量 类名"),
      rule("Services layer may only import the domain layer",
           "aurora,python",
           "services 层只允许 import domain 层，绝不能 import 其它业务模块的实现或基础设施细节。依赖方向始终向内，避免出现循环依赖和跨层意外耦合。发现反向依赖必须立刻拆，不允许用 TYPE_CHECKING 当长期借口。",
           "架构 分层 services domain import 依赖边界"),
  ])

R(2, "build",
  "再加两条质量规范：异常处理和提交流程。",
  "给 PaymentService 的方法加统一错误处理。",
  "aurora,quality", "error workflow commit", "异常 提交 质量",
  [
      rule("Throw AuroraError subclasses for all errors; never bare raise",
           "aurora,quality",
           "所有异常统一抛出我们自定义的 AuroraError 及其子类，禁止在任何地方直接 raise Exception 或裸 raise。这样上层能统一捕获、统一映射错误码、统一记日志。第三方异常必须在边界转换成 AuroraError，不要让 SDK 类型漏进业务。",
           "异常处理 AuroraError 子类 裸 raise 错误码"),
      rule("Run ruff and mypy clean before every commit",
           "aurora,quality",
           "每次提交代码前必须跑 ruff 和 mypy，两个都要全绿通过才能提交。我们不接受任何带 warning 或类型错误的提交进入主干，CI 里也会强制校验。本地 pre-commit 钩子应默认开启。",
           "工作流 提交 ruff mypy 类型检查 主干"),
  ])

R(3, "build",
  "接口约定：数据时间戳和 REST 信封。",
  "实现订单查询接口 GET /api/v1/orders 的骨架。",
  "aurora,interface", "timestamp rest api envelope", "时间戳 接口 REST API",
  [
      rule("Store timestamps as UTC ISO8601 strings",
           "aurora,interface",
           "数据库所有时间戳字段统一存 UTC 的 ISO8601 字符串，不要存本地时间也不要存时间戳整数。跨时区、跨服务、跨语言序列化时才不会出乱子。应用层计算一律 UTC，只在最外层渲染时转用户时区。",
           "时间戳 UTC ISO8601 数据库 字段"),
      rule("Use REST /api/v1 with {code,data,message} response envelope",
           "aurora,interface",
           "所有 HTTP 接口走 REST 风格，路径统一加 /api/v1 前缀，响应体统一用 {code, data, message} 三段式包裹。前端和网关都按这个约定做解析和错误处理。列表接口另须返回 page、page_size、total。",
           "接口 REST 前缀 /api/v1 响应包裹 code data message"),
  ])

R(4, "build",
  "安全规范：密钥和鉴权。",
  "给登录接口加上鉴权校验，密钥不要写进仓库。",
  "aurora,security", "secrets auth csrf", "密钥 鉴权 安全 CSRF",
  [
      rule("Never store secrets in git or container images; inject from a KMS",
           "aurora,security",
           "密钥、证书、数据库口令一律走密钥管理服务注入，禁止写入仓库、配置文件明文或镜像层。日志与导出不得出现 token、身份证号或银行卡号。轮换密钥时只改注入点，不改业务代码。",
           "密钥 KMS 明文 仓库 镜像 脱敏"),
      rule("Gateway authenticates; services re-check authorization on every write",
           "aurora,security",
           "鉴权在网关统一执行并下发身份，服务端对写操作必须二次校验权限，不能只信网关头。状态变更接口启用 CSRF 校验或同源令牌。外部输入先校验后使用。",
           "鉴权 网关 权限 CSRF 输入校验"),
  ])

R(5, "build",
  "测试规范：框架和隔离。",
  "为 billing 模块补单测骨架。",
  "aurora,testing", "pytest coverage mock", "测试 pytest 覆盖率 mock",
  [
      rule("Unit tests use pytest; core modules require 80 percent line coverage",
           "aurora,testing",
           "单元测试统一使用 pytest，文件与函数以 test_ 开头并可独立运行。核心模块行覆盖率不得低于 80%，关键路径必须覆盖分支。每次提交前本地跑通测试，CI 上单测与 lint 双重校验。",
           "测试 pytest 覆盖率 80 分支 CI"),
      rule("Unit tests must not hit real network or databases; mock at the boundary",
           "aurora,testing",
           "单测禁止依赖真实网络与数据库，外部依赖一律 mock 或桩替换。共用夹具放在 conftest.py。断言验证行为而非实现细节，避免 over-mocking 导致假绿。",
           "单测 mock 隔离 数据库 网络 conftest"),
  ])

R(6, "build",
  "运维规范：日志和健康检查。",
  "给服务加上 JSON 日志和探针。",
  "aurora,ops", "logging health probe trace_id", "日志 健康检查 探针 trace_id",
  [
      rule("Emit structured JSON logs with trace_id; never print",
           "aurora,ops",
           "日志统一输出结构化 JSON，禁止 print 与裸文本拼接。每个请求贯穿唯一 trace_id。严禁输出密码、token 等敏感字段。关键业务动作与外部调用必须留痕，包含入参摘要与耗时。",
           "日志 JSON 结构化 print trace_id 脱敏"),
      rule("Expose readiness and liveness probes; failed probes remove traffic",
           "aurora,ops",
           "服务必须暴露 readiness 与 liveness 探针，失败自动摘流。探针不得走会阻塞的下游调用。发布走灰度，每次发布保留上一稳定版本以便一键回滚。",
           "健康检查 readiness liveness 探针 灰度 回滚"),
  ])

R(7, "build",
  "评审规范：公开接口变更和 PR 描述。",
  "准备把内部查询接口改成公开 API，先对齐评审要求。",
  "aurora,review", "code review public API pull request", "评审 公开接口 PR 回滚",
  [
      rule("Public API changes require two reviewers including the interface owner",
           "aurora,review",
           "凡改动对外契约（路径、字段、错误码）的 PR 必须两名评审通过，其中一名为接口负责人。内部重构若未改变契约可一人评审。评审意见未关闭不得合并。",
           "评审 公开接口 两人 接口负责人 PR"),
      rule("Every pull request must list risk, rollout, and rollback",
           "aurora,review",
           "PR 描述必须写明改动风险、灰度步骤与一键回滚办法。缺少这三项的 PR 直接退回，不进入评审队列。",
           "PR 风险 灰度 回滚 描述"),
  ])

R(8, "build",
  "配置规范：环境变量和功能开关。",
  "把超时和开关从代码里拆出去。",
  "aurora,config", "twelve factor env feature flag", "配置 环境变量 功能开关",
  [
      rule("Read runtime config from the environment; never hardcode host or timeout",
           "aurora,config",
           "主机、端口、超时、连接池大小一律从环境变量或配置中心读取，禁止写死在源码或镜像层。缺省值只允许出现在本地开发样例，生产必须显式注入。",
           "配置 环境变量 超时 连接池 十二要素"),
      rule("Feature flags default off in production and must have an expiry owner",
           "aurora,config",
           "生产环境功能开关默认关闭。每个开关必须登记负责人与过期日，到期未清理视为缺陷。开关判断集中在配置层，禁止散落在业务分支深处。",
           "功能开关 默认关闭 过期 负责人"),
  ])

COMPLY = [
    (9, "aurora,python", "PascalCase identifiers snake_case helpers",
     "类名 PascalCase 函数 snake_case 命名",
     "给 user_service 补类型注解。", "给 user_service.py 的所有公开函数补全类型注解。"),
    (10, "aurora,python", "service import domain only inward dependency",
     "分层 services 只依赖 domain 向内",
     "拆一个跨层引用。", "把 UserService 里误 import 的 ORM session 挪到 repository。"),
    (11, "aurora,quality", "custom exception hierarchy not bare Exception",
     "异常 AuroraError 不要裸 raise",
     "给 payment_service 加错误处理。", "PaymentService.charge 失败时抛领域异常。"),
    (12, "aurora,quality", "lint typecheck before commit ruff mypy",
     "提交前 ruff mypy 全绿",
     "准备提 PR。", "列出提交前必须跑绿的检查命令。"),
    (13, "aurora,interface", "UTC ISO8601 created_at updated_at",
     "时间戳 UTC ISO8601 字段",
     "订单模型加时间字段。", "新增 Order schema 的 created_at / updated_at。"),
    (14, "aurora,interface", "REST envelope code data message api v1",
     "REST 响应包裹 /api/v1",
     "订单接口规范返回结构。", "给订单接口实现统一 {code,data,message} 响应。"),
    (15, "aurora,security", "KMS inject secrets never commit tokens",
     "密钥 KMS 不要进 git",
     "有人把密码写进 yaml 了。", "说明密钥应如何注入，以及仓库里不该出现什么。"),
    (16, "aurora,security", "recheck authorization CSRF write paths",
     "写接口鉴权 CSRF",
     "加一个改密码接口。", "说明网关鉴权之后服务端还要做什么。"),
    (17, "aurora,testing", "pytest coverage eighty percent",
     "pytest 覆盖率 80%",
     "两个 service 补测试。", "为 user_service 和 payment_service 补 pytest，覆盖核心分支。"),
    (18, "aurora,testing", "mock network database unit tests",
     "单测 mock 禁止真库",
     "有人单测连了 staging 库。", "改成边界 mock，夹具放到 conftest。"),
    (19, "aurora,ops", "structured json log trace_id no print",
     "JSON 日志 trace_id 不要 print",
     "给 payment_service 加日志。", "补结构化 JSON 日志，不要用 print。"),
    (20, "aurora,ops", "readiness liveness health probe",
     "readiness liveness 健康检查",
     "K8s 探针怎么配。", "给服务加上 readiness 与 liveness，失败摘流。"),
    (21, "aurora,review", "two reviewers public contract change",
     "公开接口 两名评审 负责人",
     "要把内部接口公开。", "列出合并前必须满足的评审条件。"),
    (22, "aurora,review", "PR risk rollout rollback description",
     "PR 风险 灰度 回滚",
     "这份 PR 描述太短。", "按规范补风险、放量和回滚说明。"),
    (23, "aurora,config", "environment variables twelve-factor config",
     "环境变量 配置 禁止写死",
     "超时写在常量里了。", "改成从环境读取，并说明生产必须显式注入。"),
    (24, "aurora,config", "feature flag default off expiry owner",
     "功能开关 默认关闭 过期",
     "要加一个实验开关。", "说明生产默认值、负责人和清理期限。"),
]

for n, scope, query, qlocal, user, task in COMPLY:
    R(n, "comply", user, task, scope, query, qlocal, [])


def main():
    rules_total = sum(len(r["new_rules"]) for r in ROUNDS)
    payload = {
        "meta": {
            "project": "aurora",
            "project_desc": "Python FastAPI 微服务",
            "rounds": len(ROUNDS),
            "build_rounds": sum(1 for r in ROUNDS if r["phase"] == "build"),
            "compliance_rounds": sum(1 for r in ROUNDS if r["phase"] == "comply"),
            "rules_total": rules_total,
            "themes": ["python", "quality", "interface", "security",
                       "testing", "ops", "review", "config"],
            "note": "前 8 轮建立 16 条规范；后 16 轮为遵守/复用（含改述与中文 query_local）。find scope 为 AND。",
        },
        "rounds": ROUNDS,
    }
    out = os.path.join(BASE, "dialogues.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("wrote", out, "rounds", len(ROUNDS), "rules", rules_total)


if __name__ == "__main__":
    main()
