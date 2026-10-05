# Step 4: Write the agent loop

**File:** `backend/app/agent.py`

This is the heart of the session. An "agent" is just this loop:

```
messages = [system, ...conversation]
loop:
    response = model(messages, tools)
    if response has no tool calls:  done
    for each tool call:  run it, append the result to messages
```

## 4.1 System prompt

Put a system message at the front of the conversation:

```python
SYSTEM_PROMPT = """You are a customer support agent.
If the message is a greeting, small talk, or doesn't describe a support issue,
reply briefly and ask how you can help. Do not call any tools.

If it is a support ticket:
1. classifyTicket
2. searchKnowledgeBase with the category
3. draftReply using what you found
4. sendReply with the draftId
Then summarise what you did in one or two sentences."""

messages = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
```

> **Why the "greeting" rule matters: try sending `Hi` without it.**
> If the prompt only says "For every ticket: 1. classifyTicket…", the model treats *every* message as a ticket. Send `Hi` and it runs all four tools. Because `category` is an enum with no "none of these" option, it has to pick one, say `billing`, and then it sends a billing email to someone who only said hello.
>
> The model did exactly what the harness told it to. **The system prompt and the tool schemas are part of the harness**, and the model calls tools only because they decide it should. Giving it a "don't call any tools" path makes `Hi` a single iteration that just streams a short greeting.

## 4.2 Call the model, streaming

```python
stream = await client.chat.completions.create(
    model=MODEL,
    messages=messages,
    tools=TOOLS,
    stream=True,
)
```

## 4.3 Read the stream

The stream gives you **chunks**. Each chunk has a `delta` that holds either text, or *pieces* of tool calls.

- Text arrives in `delta.content`. Yield it straight to the UI.
- Tool calls arrive in fragments in `delta.tool_calls`. Each fragment has an `index`. The first fragment for an index carries the `id` and `function.name`, and the rest carry bits of the `function.arguments` JSON string. **Stitch them together by `index`.**

```python
text = ""
calls: dict[int, dict] = {}   # index -> {"id", "name", "arguments"}

async for chunk in stream:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta

    if delta.content:
        text += delta.content
        yield event("message.delta", text=delta.content)

    for tc in delta.tool_calls or []:
        call = calls.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
        if tc.id:
            call["id"] = tc.id
        if tc.function and tc.function.name:
            call["name"] += tc.function.name
        if tc.function and tc.function.arguments:
            call["arguments"] += tc.function.arguments
```

## 4.4 Remember what the model said

Before you run any tool, append the **assistant** message, including its `tool_calls`. Without it, the API rejects the tool results that follow.

```python
assistant_msg = {"role": "assistant", "content": text or None}
if calls:
    assistant_msg["tool_calls"] = [
        {
            "id": c["id"],
            "type": "function",
            "function": {"name": c["name"], "arguments": c["arguments"]},
        }
        for c in calls.values()
    ]
messages.append(assistant_msg)
```

## 4.5 No tool calls? Done.

```python
if not calls:
    yield event("run.completed", runId=run_id, iterations=iteration)
    return
```

## 4.6 Run every tool call

```python
for c in calls.values():
    args = json.loads(c["arguments"] or "{}")
    yield event("tool.requested", toolCallId=c["id"], name=c["name"], args=args)

    result = dispatch(c["name"], args)
    yield event("tool.completed", toolCallId=c["id"], result=result)

    messages.append({
        "role": "tool",
        "tool_call_id": c["id"],
        "content": json.dumps(result),
    })
```

Every `tool_call_id` the model sent **must** get exactly one `tool` message back, or the next model call fails.

## 4.7 Put it in a loop

Wrap 4.2–4.6 in a `while True:` for now. **Step 5 replaces it with a bounded loop.** Don't ship an unbounded loop.

Also emit `run.started` before the loop and `iteration.started` at the top of each pass.

## Check
Set `USE_FAKE_AGENT = False` in `main.py` (more in step 7) and run:
```bash
curl -N -X POST localhost:8000/api/chat -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"I was charged twice this month"}]}'
```
You should see `tool.requested` / `tool.completed` for all four tools, then a run of `message.delta` events and finally `run.completed`.
