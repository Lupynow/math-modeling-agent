# 边学边做路线

## 阶段一：Python 项目与知识源

学习：

- Git 仓库、分支、提交和子模块。
- `pyproject.toml`、虚拟环境与包结构。
- Markdown 知识库和 JSON Schema。

实践：

1. 运行 `git submodule status`，理解 Agent 仓库与 Skill 仓库的边界。
2. 运行 `scripts/validate_knowledge.py`。
3. 阅读 `schemas/paper-ready.schema.json`，解释为什么未运行结果使用 `planned`。
4. 跟踪知识文件如何被按标题切分。

面试表达：

> 我把领域知识与应用代码拆成两个仓库，通过只读子模块锁定知识版本，避免复制内容或让应用改动污染原 Skill。

## 阶段二：FastAPI 与 MySQL

学习：

- 路由、Pydantic 请求/响应、异常处理。
- 文件上传、UUID、SHA-256 和输入校验。
- MySQL 表设计与 Repository 模式。

实践：

1. 使用 Swagger 上传一份 Markdown 赛题。
2. 跟踪 `document_id` 从接口进入 Repository 的过程。
3. 输入无效文件，观察统一 422 错误和请求 ID。
4. 查看运行记录中的 Schema 版本、Prompt 版本和指标。

面试表达：

> 路由不直接操作数据库，测试使用内存 Repository，生产环境替换为 MySQL，从而兼顾速度和可测试性。

## 阶段三：RAG 与 Agent

学习：

- Embedding、余弦相似度、Top-K 和引用元数据。
- Qdrant collection、payload 与幂等索引。
- 原生状态机、工具调用和失败边界。
- OpenAI-compatible Chat/Embedding 接口。

实践：

1. 查看检索命中的 `source_path`、`section` 和 `score`。
2. 输入同时包含预测与优化的赛题，观察多类型分类。
3. 对比候选模型的前提、优点和风险。
4. 关闭模型配置，观察 `/ready` 和 503 错误。

面试表达：

> LLM 负责开放式问题理解；候选模型、引用、验证和 Schema 由确定性代码约束，降低幻觉和不可测试性。

## 阶段四：测试、评测与 Docker

学习：

- pytest、Mock、集成测试和测试分层。
- 分类准确率、Schema 有效率和引用有效率。
- Ruff、Mypy、GitHub Actions、Docker Compose。
- 日志、延迟、token 和工具成功率。

实践：

1. 为一种问题类型新增合成赛题。
2. 模拟模型返回非法 JSON，观察一次修复重试。
3. 运行离线评测并阅读报告。
4. 比较 Fake 单元测试与 MySQL/Qdrant 集成测试。

面试表达：

> CI 使用 Fake Model 保持确定性，真实数据库和向量库单独做集成测试，真实模型评测则保留版本和指标。

## 每周节奏

- 第一天：学习知识点并读核心代码。
- 第二天：手动调用接口。
- 第三天：修改一个小功能。
- 第四天：补测试并制造失败案例。
- 第五天：用三分钟讲清输入、输出、数据流、失败方式和设计取舍。
