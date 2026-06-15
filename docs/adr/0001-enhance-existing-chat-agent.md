# Enhance Existing Chat Agent

We decided to migrate the Claude Code Learning Agent capabilities into the existing `/chat` and `/chat/stream` LangGraph flow instead of creating a separate coding-agent endpoint. This preserves the current authentication, checkpoint, streaming, and Langfuse tracing path while making the default chat Agent more capable; the trade-off is that Tool Policy must become strict enough for high-risk tools exposed in normal chat.
