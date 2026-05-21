# AI Coding Workflow: 任务状态机

## 任务状态

```text
todo      待开始
ready     依赖已满足，可以开工
doing     正在执行
blocked   被外部条件阻塞
review    已实现，等待检查
done      验收通过
archived  不再执行，仅保留历史
```

状态流转：

```text
todo -> ready -> doing -> review -> done
                 └────-> blocked -> ready
done -> archived
```

## 任务模板

```md
# TASK-000

状态: todo
负责人: codex
依赖: none
优先级: P0
模块: strategy

目标:
- 完成什么

范围:
- 包含什么
- 不包含什么

验收:
- 可验证条件 1
- 可验证条件 2

交付:
- 文件路径或接口路径
- 测试命令

备注:
- 风险、假设、后续任务
```

## 执行规则

- 实现前先把对应 TASK 状态改为 `doing`。
- 完成代码和验证后改为 `review`。
- 验收通过后改为 `done`。
- 被阻塞时改为 `blocked` 并写清原因。
- 不允许一个任务混入多个无关模块。
- 任务编号递增，不复用。
- 高危操作任务必须写清回滚方式。

