# miraita-plugin-at-command

miraita-plugin-at-command 可用于在有人发送「@机器人」时触发特定指令。

## 配置项

### execute

- 类型：`string`
- 默认值：`'help'`

要调用的指令

### allow_arguments

- 类型：`boolean`
- 默认值：`false`

是否将「@机器人」后的消息元素作为参数传递给要调用的指令

## 相关

- [`koishi-plugin-at-command`](https://common.koishi.chat/zh-CN/plugins/at-command.html) Koishi @指令
