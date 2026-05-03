# miraita-plugin-feedback

feedback 指令用于向开发者反馈信息。

## 指令：feedback

- 基本语法：`feedback <message>`
- 选项：
    - `-r, --receive` 添加到反馈频道列表 (需要 3 级权限)
    - `-R` 从反馈频道列表移除 (需要 3 级权限)

feedback 指令用于向开发者反馈信息。当有人调用 feedback 指令时，传入的 message 就会自动被发送给所有监听反馈的频道。你可以直接回复收到的反馈信息，机器人会把这些消息重新发回到调用 feedback 指令的上下文。

## 配置项

### broadcast_delay

- 类型：`int`
- 默认值：`0

向多个反馈接收频道发送时的间隔，单位为秒。

## 相关

- [`koishi-plugin-feedback`](https://common.koishi.chat/zh-CN/plugins/feedback.html) Koishi 反馈插件
