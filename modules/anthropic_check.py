import anthropic

client = anthropic.Anthropic()

try:
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=100,
        messages=[
            {"role": "user", "content": "Say hello"}
        ]
    )
    print("Success:", message.content[0].text)
except Exception as e:
    print("Error:", e)