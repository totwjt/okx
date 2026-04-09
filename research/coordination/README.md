# Coordination

这里存放双线程协作所需的信号与进度记录。

目录约定：

- `signals/<strategy_slug>/`: 线程之间的 JSON 信号文件（按策略隔离）
- `progress/<strategy_slug>/`: 两个线程各自的当前进度记录（按策略隔离）
- `templates/`: 可复制的信号模板

专用线程启动文件：

- [`thread1-profile-optimization.md`](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/coordination/thread1-profile-optimization.md)
- [`thread2-spec-optimization.md`](/Users/wangjiangtao/Documents/AI/AI-OuYi/research/coordination/thread2-spec-optimization.md)

只有明确使用这两份任务文件启动的新线程，才进入双线程 signal 协作机制。

当前线程角色：

- 线程一：`Profile Optimization Thread`
- 线程二：`Spec Optimization Thread`

策略切换时必须新建新的 `<strategy_slug>` 目录，不允许复用旧策略目录里的 current/signal 内容。
