# slides2course · 课件到课程视频

把一个学期的课件，做成一套课程视频。不是"把 PPT 念一遍"，是让一个**先修已经忘光的人**真的能听懂、能做对。

九阶段流水线，两道独立评审：AI 扮演刚毕业的高中生闭卷试读讲稿，成片后再试看一遍，不过闸不定稿。

这是一个 Agent Skill，适用于任何能读 `SKILL.md` 的 agent（OpenCode、Claude Code、Codex 等）。

---

## 它解决什么问题

做课程视频最常见的失败不是画面不好，是**讲浅了**：

- 定义直接给，没有动机，学生只能背。
- 推导跳步，作者自己补全了，观众补不上。
- 例题讲完没有检验，算错了也看不出来。
- 全课压在一小时里，只能讲目录。

这条流水线用两道**独立评审**把这些问题挡住：讲稿定稿前，让一个不知道设计意图的 agent 扮演刚高考完的学生，闭卷读、闭卷做；成片交付前，再让另一个 agent 只看字幕与关键帧复述与做题。两处都通过，才允许定稿。

---

## 流水线

```
课件 PPT / PDF / 讲义
        │
        ▼
S0  立项 ──────────► course.yaml（受众、先修、时长、交付）
        ▼
S1  拆课 ──────────► 知识图谱 + 术语表 + 逐讲拆解
        ▼
S1.5 先修诊断 ─────► 每个先修点的重建方案（默认只保留 20% 记忆）
        ▼
S2  找技能 ────────► skills.lock.md（讲法 / 素材 / 生产，三类分开）
        ▼
S3  分集 ──────────► 课时预算 + 单集目标
        ▼
S4  写稿 ──────────► 六拍 / 四槽位 / 五段式
        ▼
S5  作者审稿 ──────► 学科 / 教学 / 制作，三视角分开
        ▼
S6  学生试读 ◄──┐   独立 agent，闭卷，做变式
        │ 不通过 ─┘
        ▼ 通过
S7  制作 ──────────► code-course-video 渲染
        ▼
S8  学生试看 ◄──┐   另起 agent，只看字幕 + 关键帧
        │ 不通过 ─┘
        ▼ 通过
S9  定稿 ──────────► 版本锁 + 哈希 + 章节目录
```

---

## 三条铁律

1. **先修不重建，评审必失败。** 默认基线是「刚高考完、先修课基本忘光」，不是「学过但生疏」。
2. **稿子不过试读，不进渲染。** 改稿的成本是重渲染的几十分之一。
3. **评审必须换人。** 每轮新开上下文，不告知这是测试，不给答案。

---

## 安装

```bash
git clone https://github.com/yikai666/slides2course.git \
  ~/.config/opencode/skills/slides2course
```

其他客户端放到对应的 skills 目录即可（Claude Code 是 `~/.claude/skills/`，Codex 是 `~/.codex/skills/`）。

依赖：Python 3.9+（只用标准库）。

上游技能按需安装，不装也能跑，只是某些阶段要手工替代：

| 阶段 | 首选 | 没有时 |
| --- | --- | --- |
| S1 拆课 | `summarize-slides-skill` | `pptx` / `pdf`，或直接读文件 |
| S4 讲法 | `dialogue-tutor` 的行行推导 | 本技能的 `script-spec.md` 已内置改写版 |
| S7 制作 | `code-course-video` | 任何能出 MP4 的渲染链 |

---

## 快速开始

```bash
# 1. 建工程（<skill-dir> 是本技能所在目录）
python <skill-dir>/scripts/init_course.py ./random-signal \
  --title "随机信号分析" --slug random-signal-analysis \
  --episodes 12 --minutes 45

# 2. 填课程契约
#    编辑 course.yaml：受众、先修、平台、时长

# 3. S1 拆课，填 knowledge-map.md
# 4. S1.5 先修诊断，填 prerequisites.md
# 5. S2 找技能，填 skills.lock.md
# 6. S3 分集，填 episodes.yaml 与 EP01.md

# 7. 写稿后检查密度
python <skill-dir>/scripts/check_script.py manuscript/EP01/script.md --minutes 45

# 8. 阶段门禁
python <skill-dir>/scripts/gate.py . --episode EP01 --stage S6
```

---

## 目录

```
slides2course/
├── SKILL.md                      # 主文件：范围、铁律、九阶段
├── references/
│   ├── pipeline-contract.md      # 每阶段的产物、字段、通过条件、回退
│   ├── script-spec.md            # 六拍 / 四槽位 / 五段式 / 密度阈值
│   ├── learner-simulation.md     # 学生模拟协议：角色卡、反奉承、评分
│   ├── skill-discovery.md        # 技能检索、三类区分、锁定表
│   └── video-handoff.md          # 与 code-course-video 的字段映射
├── assets/
│   ├── course.yaml.tmpl
│   ├── episode.md.tmpl
│   ├── script.md.tmpl
│   ├── shots.yaml.tmpl
│   └── review-report.md.tmpl
├── examples/
│   └── random-signal-ep05-excerpt.md   # 校准样本：自相关函数
├── scripts/
│   ├── init_course.py
│   ├── check_script.py
│   └── gate.py
└── LICENSE
```

---

## 设计取舍

**为什么用「刚高考完」而不是「零基础」？**
零基础没有参照点，评审会问出课程无法回答的问题。刚高考完有一个确定的数学边界：会导数、概率初步、三角函数，不会积分、线代、复变。这条边界可检验。

**为什么先修只保留 20%？**
因为观众不会为了看你的课先去补三门课。先修补齐的预算必须写进课时，通常占 15%–25%。不写进预算，就会在讲的时候"顺便提一句"，然后观众掉队。

**为什么评审不能复用？**
同一段上下文里，评审会继承上一轮的讲法印象，第二轮会不自觉地补全。换人是唯一可靠的办法。

**为什么视频阶段还要审一次？**
讲稿通过只说明文字能读懂，不说明画面接得住。字幕与画面错位、一句话里三个对象、检查点停顿不够，都只在成片阶段暴露。

---

## 已知局限

- **代理不能真的看视频。** S8 只能读字幕与关键帧，判断不了语速、音质、口播错误、动效。报告里必须声明，另配人工抽查。
- **学科正确性靠上游。** 本技能管讲法，不管公式对不对。S5 的学科审稿不能省。
- **不生成学科素材。** 波形、谱图、仿真要么来自上游工具，要么自建，记录在 `skills.lock.md`。

---

## License

MIT
