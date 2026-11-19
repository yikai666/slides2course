# 阶段契约

本文件定义每个阶段的输入、动作、产物、字段和通过条件。SKILL.md 给顺序，这里给可执行的细节。

## 目录约定

```
<course>/
├── course.yaml
├── progress.json
├── content/
│   ├── knowledge-map.md
│   ├── glossary.md
│   ├── prerequisites.md
│   └── lectures/L01.md
├── tooling/skills.lock.md
├── plan/
│   ├── episodes.yaml
│   └── EP01.md
├── manuscript/EP01/{script.md,examples.md,shots.yaml}
├── reviews/EP01-{author,learner-r1,watch-r1}.md
├── video/EP01.mp4
└── delivery/manifest.json
```

课程 ID 用 `EP01`、`EP02`，不补零到三位，方便排序又不易写错。知识点 ID 用 `K-<章>-<序>`，例如 `K-05-02`。

---

## S0 立项

**输入**：用户的课程名、课件、目标平台、时长要求。

**动作**：填 `course.yaml`。凡是不确定的，写 `待定` 并列进 `open_questions`，不要自己编。

**产物**：`course.yaml`

```yaml
title: 随机信号分析
slug: random-signal-analysis
audience:
  baseline: 刚高考完
  prerequisites_retained: 0.2   # 先修只保留 20%
  math_level: 高中数学 + 本课重建
prerequisites:
  declared: [概率论, 微积分, 复变函数, 信号与系统]
  rebuild_policy: 每个先修点首次出现时 2 分钟内重建
delivery:
  platform: bilibili
  episode_minutes: 45
  tolerance_minutes: 8
  captions: true
  resolution: 1920x1080
  fps: 30
  voice: zh-CN-XiaoxiaoNeural
  output_dir: video
open_questions:
  - 教材版本未定
```

**通过条件**：`audience.baseline`、`prerequisites.declared`、`delivery.episode_minutes` 三项非空；`open_questions` 已读给用户确认。

---

## S1 拆课

**输入**：课件文件（pptx / pdf / 讲义 / 录音转写）。

**动作**：

1. 优先调 `summarize-slides-skill`。它没装就用 `pptx` / `pdf`。
2. 建知识点表。每行：ID、名称、所属章、来源页、难度（1–5）、是否重点。
3. 建依赖边。只写「A 必须先于 B」且给出理由，不要写"A 相关 B"。
4. 建术语表。每行：中文、英文、符号、读法、首次出现位置。

**产物**：

- `content/knowledge-map.md`
- `content/lectures/L01.md` …… 每讲一份
- `content/glossary.md`

`knowledge-map.md` 格式：

```markdown
## 第 5 章 随机过程的功率谱

| ID | 知识点 | 来源页 | 难度 | 重点 |
| --- | --- | --- | --- | --- |
| K-05-01 | 功率谱密度的定义 | 88–91 | 3 | 是 |
| K-05-02 | Wiener–Khinchin 定理 | 92–96 | 4 | 是 |

### 依赖边

- K-05-02 依赖 K-05-01：先有谱的定义，才能谈谱与相关函数的对应。
- K-05-02 依赖 K-03-04：要会用傅里叶变换。
```

**通过条件**：

- 课件总页数 = 已归属页数 + 明确排除页数。
- 依赖图无环（用 `gate.py` 的 `--check-deps` 或人工过一遍）。
- 每个知识点至少一个来源页。

---

## S1.5 先修诊断

**输入**：`knowledge-map.md`、`course.yaml`。

**动作**：对每个知识点列最小先修集，给重建方案或绕开方案。

**产物**：`content/prerequisites.md`

```markdown
| 先修 ID | 名称 | 被谁依赖 | 重建方式 | 预算 | 讲稿位置 |
| --- | --- | --- | --- | --- | --- |
| P-01 | 随机变量与分布 | K-03-01, K-03-02 | 3 分钟：抛硬币 → 取值 → 分布 | 3 min | EP02 00:04:10 |
| P-02 | 期望与方差 | K-03-01, K-05-01 | 4 分钟：加权平均 → 物理意义 | 4 min | EP02 00:07:30 |
| P-03 | 傅里叶变换 | K-05-02 | 不重建，改讲法：只用到"时域卷积=频域相乘" | 0 | EP05 00:12:00 |
```

**通过条件**：

- 所有标记为"是"（重点）的知识点，其先修都有重建或绕开方案。
- 先修总预算 ≤ 全课时长的 25%。超过就要在 S3 单独成集。

---

## S2 找技能

**输入**：知识点表、课程类型。

**动作**：按 `skill-discovery.md` 检索、评估、记录。**不擅自安装。**

**产物**：`tooling/skills.lock.md`

```markdown
| 技能/工具 | 来源 | 版本/commit | 类型 | 用途 | 结论 | 理由 |
| --- | --- | --- | --- | --- | --- | --- |
| dialogue-tutor | github:jinshanbaihai | 2026-09 | 教学法 | 推导行四槽位 | 采用（改写） | 讲法密度足够，但不直接产出视频稿 |
| random-signal-agent | github:PatrickStar-cmd | v0.4.11 | 内容/素材 | 生成 AR、Welch 图 | 采用 | 固定种子可复现 |
| signal-processing | clawhub:viewway | - | 内容 | 随机信号章节 | 参考 | 只作知识核对，不作讲法 |
```

**通过条件**：每个知识点至少有一行"讲法归属"；每个需要画面的知识点至少有一行"素材来源"或明确写"自建"。

---

## S3 分集

**输入**：知识图谱、先修诊断、时长约束。

**动作**：切集、写目标、算预算。

**产物**：

- `plan/episodes.yaml`
- `plan/EP01.md`

`episodes.yaml`：

```yaml
episodes:
  - id: EP01
    title: 从确定性到随机
    knowledge: [K-01-01, K-01-02]
    prerequisites: [P-01]
    minutes: 42
    objectives:
      - 能说出随机信号与确定性信号的区别
      - 能判断一个信号是否需要用随机模型
```

`EP01.md` 要写：3–5 个可测目标、知识点清单、每 5 分钟的画面类型、开头钩子、结尾钩子（指向下一集）。

**通过条件**：

- 每集 `minutes` ≤ `episode_minutes + tolerance`。
- 目标数 3–5，且都以"能算出/能判断/能解释/能画出"开头。
- 知识图谱中每个知识点恰好属于一集（允许复习集重复）。

---

## S4 写稿

**输入**：`plan/EP01.md`、知识点、先修方案。

**动作**：按 `script-spec.md` 写三个文件。

**产物**：

- `manuscript/EP01/script.md`
- `manuscript/EP01/examples.md`
- `manuscript/EP01/shots.yaml`

**通过条件**：

- `check_script.py` 退出码 0。
- `examples.md` 里每道例题都有：题干、答案、变式（至少 1 道）、常见错误。
- `shots.yaml` 的每个 shot 都有 `narration_ref`，能指回 `script.md` 的段落编号。

---

## S5 作者审稿

**输入**：S4 三个产物。

**产物**：`reviews/EP01-author.md`

模板：

```markdown
# EP01 作者审稿

## 学科
- [ ] A-01（blocking）第 3 段：Wiener–Khinchin 定理漏了"广义平稳"条件。改：在定理前加一句前提。

## 教学
- [ ] T-01（blocking）00:12:30 直接写出 R_X(τ)=E[X(t)X(t+τ)]，没有解释"为什么乘的是同一过程"。改：先用两条样本函数演示"自己的和延迟后的自己"。

## 制作
- [ ] P-01（non-blocking）第 7 段一句话里有三个对象，画面无法同时高亮。改：拆成两句。

## 结论
blocking: 2，non-blocking: 1 → 不通过
```

**通过条件**：blocking = 0。

---

## S6 学生试读

**输入**：`script.md` + `examples.md` 的**题干部分**。不给答案。

**动作**：按 `learner-simulation.md` 起一个独立 subagent，跑三个任务。

**产物**：`reviews/EP01-learner-r1.md`

**通过条件**：

```
理解均分 ≥ 2.5/3
例题正确率 ≥ 80%
blocking 卡点 = 0
```

不通过：把每个 blocking 卡点映射到 `script.md` 的具体行，标"缺的是什么"，回 S4。

**注意**：下一轮必须新开 subagent。复用上一轮的评审，等于让它带着上一版讲法去读新版。

---

## S7 制作

**输入**：`script.md`、`shots.yaml`、`examples.md`。

**动作**：映射成 `code-course-video` 的三件套，渲染。

**产物**：`video/EP01.mp4`、`video/EP01.course.json`、`video/EP01.anchors.json`、`video/EP01.words.json`

**通过条件**：

- `timeline_tools.py validate` 通过。
- 试片 60–90 秒人工看过。
- 高亮覆盖率报告：每个知识点至少一次持续选中。

详见 `video-handoff.md`。

---

## S8 学生试看

**输入**：字幕全文（带时间戳）、每 30 秒一帧、章节表。**不给讲稿。**

**产物**：`reviews/EP01-watch-r1.md`

**通过条件**：

```
复述准确（三个要点至少两个）
检查点能答（≥ 2/3）
音画错位 = 0（blocking）
"必须回看才能懂" ≤ 2 处（non-blocking）
```

另加人工抽查：随机抽 3 分钟，看语速、音量、口播错误。代理不覆盖这部分。

---

## S9 定稿

**产物**：

- `delivery/manifest.json`：文件、大小、sha256、版本。
- `delivery/chapters.txt`：`HH:MM:SS 名称`。
- `delivery/README.md`：怎么复现、依赖什么、哪些没测。

**通过条件**：manifest 里每个文件哈希可复算；`chapters.txt` 首行 `00:00:00`。

---

## progress.json

```json
{
  "course": "random-signal-analysis",
  "updated": "2026-11-19T10:00:00+08:00",
  "episodes": {
    "EP01": {
      "stage": "S6",
      "gates": {
        "S1": "pass",
        "S1.5": "pass",
        "S2": "pass",
        "S3": "pass",
        "S4": "pass",
        "S5": "pass",
        "S6": "fail"
      },
      "rounds": {"learner": 1, "watch": 0},
      "blocking": ["L-03: 没有解释为什么 PSD 非负"],
      "artifacts": {
        "script": "manuscript/EP01/script.md",
        "review": "reviews/EP01-learner-r1.md"
      }
    }
  }
}
```

`stage` 是当前所在阶段，不是最后通过的阶段。回退时把它改回去，并在 `rounds` 里加一。

---

## 回退规则

回退只回一层，不要一次跳回 S0：

| 失败点 | 先判断 | 回退 |
| --- | --- | --- |
| S4 检查不过 | 是密度不足还是结构缺失 | 密度 → 补"为什么"；结构 → 补六拍中缺的那一拍 |
| S5 学科 blocking | 是讲错还是讲浅 | 讲错 → 改内容；讲浅 → 加推导或例子 |
| S6 不理解 | 缺先修、跳步、还是术语没定义 | 分别回 S1.5、S4、S4 |
| S6 不会做 | 例题与讲法不匹配 | S4 重写例题，不是加题量 |
| S8 音画错位 | 锚点错还是分镜错 | 锚点 → 重对齐；分镜 → 改 shots |
| 多集同点卡住 | 先修系统性缺失 | S1.5，必要时加第 0 集 |

每次回退在 `progress.json` 的 `rounds` 里加一，并在评审报告里写"上一轮哪个 blocking 导致回退"。
