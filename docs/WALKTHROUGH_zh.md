# Super Crawler 智能体系统 —— 使用与构建讲解

> 面向导师演示与日常使用的中文讲解。对应英文进度见 `docs/` 下各 TASK_*.md。

## 一、这是什么

这是一个**长期运行的多智能体需求发现系统**:它从 Reddit 的真实讨论里发现用户需求,
经过**搜索规划 → 发现采集 → 需求记忆 → 队列 → 深度研究**这条流水线,得出**可追溯、可验证、
可恢复**的结论,并通过仪表盘和客户报告呈现给人看。

核心理念(和培训 PPT 一致):**LLM 只是其中一个决策模块;真正让它成为"系统"的,是状态机、
队列、工作器、日志、可观测性和失败恢复。**

## 二、如何打开

- 仪表盘地址:**http://127.0.0.1:8400**
  (本机 8000 端口被 Windows 的 HTTP.sys 占用,所以用 8400。)
- 智能体已经作为常驻进程在跑;每 **300 秒**自动跑一个完整周期。
- 看门狗脚本 `deploy/start_super_crawler.ps1` 负责崩溃自动重启,日志在 `deploy/logs/`。

命令行(在克隆目录 `_reference_super_crawler` 下运行,用项目自带的 venv):

```powershell
cd C:\Users\12572\project-template\_reference_super_crawler
..\.venv\Scripts\python.exe -m super_crawler.cli <命令>
```

## 三、仪表盘逐区讲解(Running Status 首页)

顶部导航:**Running Status(运行状态)/ Possible Requirements(可能的需求)/
Rejected Requirements(被否决的需求)/ Client Reports(客户报告)**。

1. **Agent Runtime(智能体运行条)**
   显示运行状态、已跑周期数、上一周期结果。三个按钮:`Start` / `Stop` 控制循环,
   **`Run Once` 立即跑一个周期** —— 这是演示时不用等 5 分钟的按钮。

2. **Global Resource Allocation(全局资源分配)**
   工作器槽位滑块。把 `Deep`(深度研究)从 1 改成 5 再 `Save Limits`,下个周期就有 5 个研究
   工作器并发 —— 不用重启进程。这就是 PPT 里"1 改 5 不必重启"的热扩容。
   注意:这里的"使用中槽位"现在统计的是**真实有心跳的工作器**,不是被锁住的队列行。

3. **Deep Workers(real state) —— 深度工作器真实状态**(Task A 新增)
   每一行是一个真实工作器:当前阶段(`analyzing_evidence → scoring → synthesizing →
   writing_conclusion → idle`)、正在处理的需求(可点)、心跳时间、出错信息。
   如果某个工作器卡死,这里会显示 **STALE(过期)**,下个周期的"回收器(reaper)"会把它的
   任务自动放回队列。**可观测性和恢复用的是同一份心跳数据。**

4. **Evaluation Metrics —— 评估指标**(Task E 新增)
   四张卡片:平均周期耗时(速度)、LLM 计算秒数(成本,本地模型用计算秒数而非美元)、
   信号率/噪音率(相关性)、验证率。下方有"发现产出率"和 `/api/metrics`(完整 JSON,可接外部监控)。
   一个真实读数:**验证率从 0.0 变成 0.2,正是在闭环跑通、第一个需求被验证的那一刻** ——
   因为指标完全从系统已记录的数据算出,不会和现实脱节。

5. **Search Plan —— 搜索计划**(Task B 新增)
   显示 LLM 规划器产出的策略:引擎标签(`ollama:qwen2.5:3b` 或 `heuristic`)、搜索维度、
   带理由的查询语句、噪音过滤词、以及它"读到的反馈"。
   关键看点:它的噪音过滤词会复现系统自己之前否决过的噪音(比如 lunchbox、meal prep)——
   **模型从系统的历史结论里学习,让下一轮搜索收敛。**

6. **状态计数卡片**:按生命周期状态统计需求数量(possible / queued / researching /
   validated / reopened / rejected)。

7. **Task group boards —— 任务组看板**:可创建 general(通用)或 domain(领域)搜索任务组,
   每个运行中的任务组有自己的三栏看板和输入文件夹。

**Possible / Rejected 两个页面**:每条需求是一整行"血缘"(从哪个搜索产出 → 证据 → 队列/池 →
深度研究 → 结论 → 流水线快照),每个标签都可点进去看细节。被否决的需求不是"墓地"——
一旦有新证据让分数上升,变更检测会自动**重开(reopen)**它。

**Client Reports —— 客户报告**(Task D 新增):同一份数据的"对客户"的另一面,纯白话,
没有任何内部术语。每条结论是:结论判定("真实需求,值得行动" / "有潜力,继续观察" /
"证据不足,可能是噪音")+ 关键数字 + 为什么真实/为什么可能是噪音 + 用户现在怎么凑合解决 +
付费意愿语句 + 地域分布 + 建议的下一步 + 可点的源证据链接。可导出成单个 HTML 文件直接发给客户。

## 四、常用命令

```powershell
# 让 LLM 生成搜索计划(并导出成采集器的爬取配置)
..\.venv\Scripts\python.exe -m super_crawler.cli plan --goal "你要研究的方向" --export-config ..\configs\plan_x.json

# 查看指标 JSON
..\.venv\Scripts\python.exe -m super_crawler.cli metrics

# 导出某条需求的客户报告(独立 HTML)
..\.venv\Scripts\python.exe -m super_crawler.cli client-report --requirement REQ-2026-000001 --out ..\reports\brief.html

# 喂真实数据:把 Reddit 风格的 JSON 数组放进 _reference_super_crawler\data\reddit_inbox\
```

## 五、这周做了什么(对应 PPT 的实习任务)

代码在 `ShuhangGe/super_crawler` 克隆里,按任务分支叠加:

| PPT 任务 | 做了什么 |
|---|---|
| **任务 C —— 失败恢复** | WAL、原子化领取队列、回收卡住的 `researching`、研究失败自动重排队 |
| **任务 A —— 工作器状态面板** | workers 表 + 心跳、真实阶段流转、Deep Workers 面板、回收器改为按心跳判断过期 |
| **部署** | 常驻智能体上线本机(看门狗、`serve --autostart`、300 秒周期) |
| **任务 B —— LLM 搜索规划器** | 本地 Ollama(qwen2.5:3b)、读深度研究反馈收敛、无模型时退回确定性规划 |
| **(闭环)** | 计划 → 实时爬取 → inbox → 研究:狗狗用药追踪需求自动跑到了 **validated**(分数 84) |
| **任务 E —— 评估指标** | 速度/成本/相关性/验证率,全部从已记录数据算出 |
| **任务 D —— 客户报告** | 给非技术客户看的需求机会简报 |

一个很值得对导师说的点:**用合成种子数据测试 100% 通过,但一接真实数据就暴露了两个真 bug**
(Windows 下 UTF-8 读取崩溃;原始正则对真实 Reddit 措辞的召回率约等于 0)。两个都已修复并加了
回归测试。这正是 PPT 第 9 页的道理:**智能体系统栽在边界条件,而不是 prompt 写得不够漂亮;
端到端跑真实数据才是唯一诚实的验证。**

参考系统测试:**37 个全绿**。每个任务的说明和精确 diff 在 `docs/` 下,均已推送到
`tophorse25/project-template` 仓库。

## 六、给导师演示的建议流程(一口气演完)

1. 打开仪表盘 → 点 `Run Once` → 看 **Deep Workers** 面板里工作器一格格走过各阶段(有心跳)。
2. 看 **Evaluation Metrics**:验证率因为闭环跑通从 0 升到 0.2。
3. 看 **Search Plan**:模型的噪音过滤词回应了系统自己否决过的噪音(反馈闭环)。
4. 点 **Client Reports** → 打开狗狗用药那条:从证据到结论到下一步,全程可追溯。
5. 收尾一句:这就是 PPT 最后一页 —— **能运行、能解释、能恢复**;LLM 只是系统里的一个模块,
   而不是系统本身。这就是"调用 AI"和"构建 AI 系统"的区别。

## 七、需要你手动做的两件事

1. **开机自启**(让智能体重启后还在跑):
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\12572\project-template\deploy\register_startup.ps1
   ```
2. **PR 权限**:目前 `tophorse25` 对 `ShuhangGe/super_crawler` 没有推送权限(403)。
   找导师要 fork 或协作者权限,这些分支就能变成正式 PR;在那之前,导师可以通过 `docs/` 里的
   diff 审阅。

## 八、局限与下一步

- 仅本机运行,仪表盘只绑定 127.0.0.1(导师需共享屏幕,或迁到团队服务器才有公开地址)。
- 浏览器搜索卡片有时取不到点赞/评论数,互动分会偏低 —— 用 deep-fetch 抓正文可补全。
- 3B 小模型偶尔漏掉 validation_hypotheses、给出未经核实的子版块 —— 换 7B 或加重试/校验即可。
- LLM 目前只用在搜索规划;候选需求的命名和深度研究综述还可以接模型(确定性分数保留作基线)。
