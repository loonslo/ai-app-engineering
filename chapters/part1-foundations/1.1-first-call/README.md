# 1.1 第一次调用大模型 API

平时调用大模型 API，如果只是写个脚本测试，传一句话拿回文本直接打印，一般不会觉得有什么问题。

但把代码接进服务跑一阵子，往往会遇到一些莫名其妙的状况：回答突然少了一半；请求卡住好几十秒；或者账单消耗对不上。

底层其实就是一个 HTTP POST 请求。发一段 JSON 过去，拿一段 JSON 回来。正文之外，返回结构里有几个字段平时很容易被忽略。

![请求与返回的主要结构](/shots/llm-request-anatomy.svg)

## 发送请求时的两个角色

传参的时候，消息列表里主要放两类内容：`system` 和 `user`。

`system` 用来定规则，比如限制回答范围、设定角色。模型在生成回答时会优先参考这个设定。`user` 则是用户发过来的具体问题。这两个字段在代码里最好做一下非空判断，传空字符串过去只是在白白浪费请求。

做具体功能时，通常会加上 `temperature=0`。数值设为 0，模型每次给出的回答会比较固定，适合系统稳定运行。

## 返回内容里的两个关键字段

拿到返回结果后，除了用来展示给用户的文字，通常还需要看一下这两个字段：

### 结束原因：finish_reason

这个字段说明了模型为什么停止生成。

如果是 `stop`，说明回答正常结束了。

如果拿到的是 `length`，说明回答太长，超过了预设的最大字数，后面的内容被直接截掉了。

遇到回答只显示一半的情况，多数时候不是模型出错，而是触碰了字数上限。在业务代码里判断这个状态，可以用来提示用户内容被截断，或者自动发起二次请求补齐内容。

### 字数消耗：usage

这个字段记录了这次调用花了多少 token。

里面分两项：输入的字数（`prompt_tokens`）和输出的字数（`completion_tokens`）。

大模型的费用和耗时主要看这两个数字。因为模型是一个字一个字往外输出的，输出越长耗时就越久，费用也越高。在生产环境里，把这两个数字记进日志，方便后续排查耗时和核对账单。

## 简单的调用代码

大模型服务商大多兼容 OpenAI 的接口规范。直接使用官方提供的 `openai` 库即可，不需要引入太重的第三方框架：

```python
import os
from openai import OpenAI

# 从系统环境变量读取 API Key 和服务地址，避免把密钥直接写死在代码里
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.deepseek.com"),
)

response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {"role": "system", "content": "你是一个严谨的技术助手，回答尽量精简。"},
        {"role": "user", "content": "用一句话解释什么是检索增强生成（RAG）？"},
    ],
    temperature=0.0,  # 设为 0，让模型输出保持稳定
)

# choices 是一个列表，默认单次请求只生成一条候选回答
choice = response.choices[0]
content = choice.message.content
finish_reason = choice.finish_reason

# usage 记录当次调用的 token 统计，读取前做一下非空判断
usage = response.usage

print("回答内容:", content)
print("结束状态:", finish_reason)
if usage:
    print(f"Token 统计: 输入 {usage.prompt_tokens}，输出 {usage.completion_tokens}")
```

这段代码里有三个细节在实际写服务时比较常用：

一是通过环境变量读取密钥，防止不小心把 Key 提交到公开代码仓库。

二是接口返回的候选回答 `choices` 是一个数组，平时默认取第 0 项就可以。

三是 `usage` 里的数字最好顺手记到系统日志里。后续如果遇到响应变慢或者费用偏高，调出日志比对输入和输出 token，能很快排查出是用户输入太长还是模型输出超长。

## 常见的报错处理

调用外部接口总会遇到报错。遇到错误时，主要分清哪些需要人工看，哪些可以自动重试。

![常见报错与应对决策](/shots/llm-error-decision.svg)

常见的一般是这三类：

401 认证错误。通常是 API Key 填错了或者账号欠费了。这种错误重试多少次都没用，直接抛出异常并通知人去检查账号配置。

429 限流。请求发得太快，服务商暂时处理不过来。这种一般等一两秒再试一次就能过去，适合自动重试。

超时。网络抖动或者服务器响应太慢。客户端需要设一个超时时间（比如 15 秒），超时之后可以重试一次，或者切到备用模型。

在业务代码里，可以写一个分类函数，用布尔值告诉上层调用能不能直接重试：

```python
import openai

def classify_api_error(err: Exception) -> dict:
    """
    根据异常类型判断是否允许重试，并给出对应的处理建议
    """
    # 401 认证异常：通常是 Key 无效、账号欠费或无访问权限
    if isinstance(err, openai.AuthenticationError):
        return {"retryable": False, "msg": "Key 无效或欠费，需人工排查"}

    # 429 限流异常：请求频率或并发超过了服务商的配额
    if isinstance(err, openai.RateLimitError):
        return {"retryable": True, "msg": "触发服务商限流，稍后退避重试"}

    # 超时异常：网络链路抖动或服务端推理耗时过长
    if isinstance(err, openai.APITimeoutError):
        return {"retryable": True, "msg": "请求超时，可重试一次或切换备用模型"}

    # 其他未预期的异常（如网络完全断开、入参格式错误）
    return {"retryable": False, "msg": f"其他错误: {err}"}
```

通过 `retryable` 这个标识，代码在捕获异常时就很容易写重试逻辑：如果是 `True`，程序等待一两秒再重新发起一次；如果是 `False`，就直接把报错抛给外层或者记进告警，避免程序把大量无效重试打在已经欠费的接口上。

## 观察截断状态

验证截断逻辑时，可以在调用参数里加上 `max_tokens=5`，强行限制模型的最大输出长度：

```python
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=[
        {"role": "system", "content": "你是一个严谨的技术助手。"},
        {"role": "user", "content": "用一句话解释什么是检索增强生成（RAG）？"},
    ],
    temperature=0.0,
    max_tokens=5,  # 限制模型最多只能输出 5 个 token
)

choice = response.choices[0]
print("返回文本:", choice.message.content)
print("结束状态:", choice.finish_reason)
```

运行这段代码，打印出来的文本通常只讲了半句话（例如“检索增强生成是”），后面的内容就没有了；此时打印出的 `finish_reason` 会明确变为 `length`。

在写接口自动化测试或核心业务时，只要判断出 `finish_reason == "length"`，就能知道当前回答并不完整，可以借此触发告警，或者提示用户调整提问。
