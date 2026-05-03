# miraita-plugin-repeater

miraita-plugin-repeater 用于检测群聊中的复读行为，并按配置复读、打断复读或响应打断复读的人。

插件只在群聊中生效。机器人自己发出的消息会被记录到复读状态中，因此默认不会对同一段内容无限复读。

## 配置项

### on_repeat

- 类型：`RepeatAction | RepeatAction[] | null`
- 默认值：`{ min_times: 2, probability: 1 }`

当检测到有人复读上一条消息时触发。默认行为是在同一句话连续出现 2 次后，由机器人复读一次。

### on_interrupt

- 类型：`RepeatAction | RepeatAction[] | null`
- 默认值：`null`

当检测到复读被其他消息打断时触发。默认不响应打断复读。

## RepeatAction

### min_times

- 类型：`int`
- 默认值：`2`

触发规则需要达到的最少复读次数。

### probability

- 类型：`float`
- 默认值：`1`

触发概率，取值范围为 `0` 到 `1`。

### content

- 类型：`string | null`
- 默认值：`null`

仅当当前复读内容与该值完全一致时触发。

### user_times

- 类型：`int`
- 默认值：`0`

当前用户参与同一句复读达到该次数时才触发。设置为 `0` 表示不限制。

### repeated

- 类型：`bool | null`
- 默认值：`null`

限制机器人是否已经复读过当前内容。设置为 `null` 表示不限制。

### reply

- 类型：`string | null`
- 默认值：`null`

触发规则后发送的回复模板。`on_repeat` 未设置 `reply` 时默认回复复读内容，`on_interrupt` 未设置 `reply` 时不会发送消息。

可用模板变量：

- `{content}` 当前复读内容
- `{times}` 当前复读次数
- `{user_id}` 当前用户 ID
- `{user_name}` 当前用户名称
- `{at_user}` @ 当前用户
- `{self_id}` 当前机器人账号 ID
- `{channel_id}` 当前频道 ID
- `{guild_id}` 当前群组 ID

## 配置示例

### 概率复读

```yaml
plugins:
  miraita.plugins.repeater:
    on_repeat:
      min_times: 3
      probability: 0.5
```

当同一句话达到 3 次后，每次继续复读都有 50% 概率触发机器人复读。

### 自动打断指定复读

```yaml
plugins:
  miraita.plugins.repeater:
    on_repeat:
      min_times: 2
      content: 这机器人又开始复读了
      reply: 打断复读！
```

### 检测重复复读

```yaml
plugins:
  miraita.plugins.repeater:
    on_repeat:
      min_times: 2
      user_times: 2
      reply: "{at_user}不许重复复读！"
```

当同一个用户对同一句话复读 2 次时提醒对方。

### 检测打断复读

```yaml
plugins:
  miraita.plugins.repeater:
    on_repeat:
      min_times: 2
    on_interrupt:
      repeated: true
      min_times: 3
      probability: 0.5
      reply: "{at_user}在？为什么打断复读？"
```

当某条消息已经被机器人复读过，且复读次数达到 3 次后，有人打断复读时以 50% 概率出警。

### 多规则

```yaml
plugins:
  miraita:
    .plugins.repeater:
      on_repeat:
        - min_times: 3
          probability: 0.5
        
        - min_times: 2
          content: 这机器人又开始复读了
          reply: 打断复读！
        
        - min_times: 2
          user_times: 2
          reply: "{at_user}不许重复复读！"
      
      on_interrupt:
        - repeated: true
          min_times: 3
          probability: 0.5
          reply: "{at_user}在？为什么打断复读？"
```

规则会按配置顺序依次检查，命中第一条有回复的规则后停止。

## 自定义回调

如果配置规则不够用，可以在 Python 中注册回调。回调会收到当前复读状态 `state` 和会话 `session`，返回字符串或 `MessageChain` 时发送消息。

```python
from arclet.entari import At, MessageChain

from miraita.plugins.repeater import on_interrupt, on_repeat


@on_repeat
def _(state, session):
    if state.times >= 2 and state.content == "这机器人又开始复读了":
        return "打断复读！"


@on_interrupt
def _(state, session):
    if state.repeated and state.times >= 3:
        return MessageChain([At(session.user.id, name=session.user.name), "在？为什么打断复读？"])
```

## 相关

- [`koishi-plugin-repeater`](https://common.koishi.chat/zh-CN/plugins/repeater.html) Koishi 复读机
