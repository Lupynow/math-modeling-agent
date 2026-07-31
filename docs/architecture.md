# 架构说明

## 设计目标

项目把原本只能被 Agent 阅读的数学建模知识，变成可以通过 API 调用、保存、评测和回归的应用。领域内容通过 `knowledge/math-modeling-skills` 只读子模块引入，应用层只负责解析、检索、编排和记录，避免复制或修改原 Skill 仓库。

## 组件职责

| 组件 | 职责 | 失败时的行为 |
|---|---|---|
| FastAPI | 校验输入、返回稳定 Schema、生成请求 ID | 返回统一错误对象 |
| Document Parser | 解析 PDF/TXT/Markdown，限制大小和类型 | 拒绝空文件、扫描 PDF 和非 UTF-8 文本 |
| Agent | 按固定状态流调用工具 | 记录失败工具和不确定性 |
| Chat Provider | 生成问题摘要、子问题和数据需求 | 有限重试后返回 502 |
| Embedding Provider | 为知识片段和查询生成向量 | 失败时不伪造检索结果 |
| Qdrant | 保存知识向量和来源元数据 | `/ready` 失败 |
| MySQL | 保存文档、运行、检索命中和评测记录 | `/ready` 失败 |

## Agent 状态与工具

Agent 不依赖 LangGraph。状态转移直接由 Python 控制，便于观察和单元测试：

1. `classify_problem`：使用可解释关键词建立初始分类。
2. `retrieve_modeling_knowledge`：检索相关 Skill 章节并保留路径、标题和分数。
3. `recommend_candidate_models`：从与问题类型对应的候选库中选择至少两个模型。
4. Chat Provider：基于赛题与检索上下文生成结构化问题理解。
5. `validate_analysis_plan`：检查候选数、引用和求解流程。
6. `render_paper_ready`：生成 JSON 和 Markdown 论文交接包。

真实模型负责语言理解和补全，分类、候选模型、引用、验证和输出结构仍由确定性代码约束。

## 数据模型

### MySQL

- `documents`：文件名、类型、SHA-256、解析文本和时间。
- `analysis_runs`：模型、Schema/Prompt 版本、完整输出和运行指标。
- `retrieval_hits`：每次运行使用的来源路径、章节和检索分数。
- `evaluation_results`：评测名称、数值和详细信息，供后续在线评测写入。

### Qdrant

Markdown 按一级至四级标题切分。每个向量点保存：

- `source_path`
- `section`
- `text`
- `content_hash`

向量点 ID 由内容哈希确定，因此对同一版本重复索引是幂等的。

## API 契约

`POST /api/v1/documents` 将文件转换为 `document_id`。
`POST /api/v1/analysis-runs` 同步执行一次分析并保存结果。
`GET /api/v1/analysis-runs/{run_id}` 返回相同的版本化结果。

第一版保持同步接口，避免为了展示而提前引入 Redis 和任务队列。出现稳定的长任务需求后，再增加异步任务层。

## 安全边界

- 文件名只取 basename，防止目录穿越。
- 文件类型采用扩展名白名单并限制读取字节数。
- 上传内容只解析为文本，不执行代码、宏或脚本。
- API Key 不入库、不写日志、不进入 Git。
- 引用只能来自已索引知识片段。
- 生产部署应把管理端口限制在内网，并为公开 API 增加认证和速率限制。
