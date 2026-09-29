# Aurora 后端规范指南

本文档是 aurora 项目（Python FastAPI 微服务）的团队规范唯一权威来源，供 imprint shelves 索引与召回。

## 命名规范

函数和变量统一用 snake_case，类名用 PascalCase。与社区 PEP8 对齐，代码 review 时一眼能分清标识符是函数、变量还是类型。

## 分层依赖

services 层只允许 import domain 层，绝不能 import 其它业务模块的实现或基础设施细节。依赖方向始终向内，避免循环依赖和跨层意外耦合。

## 异常处理

所有异常统一抛出自定义的 AuroraError 及其子类，禁止 raise Exception 或裸 raise。上层统一捕获、映射错误码、记日志。

## 提交流程

每次提交代码前必须跑 ruff 和 mypy，两个都全绿才能提交。不接受任何带 warning 或类型错误的提交进入主干，CI 强制校验。

## 时间戳规范

数据库所有时间戳字段统一存 UTC 的 ISO8601 字符串，不存本地时间也不存时间戳整数，跨时区与跨语言序列化不出乱子。

## HTTP 接口规范

所有 HTTP 接口走 REST 风格，路径统一加 /api/v1 前缀，响应体统一用 {code, data, message} 三段式包裹。前端和网关都按此约定解析和错误处理。