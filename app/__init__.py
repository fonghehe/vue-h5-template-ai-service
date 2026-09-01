"""Streaming AI companion service for vue-h5-template.

The service owns exactly one responsibility: turn a list of chat messages into
a Server-Sent Events stream that the `useStreamingChat` composable in
`@vh5/ai-chat` can consume. Model access sits behind a provider interface so
that the mock provider used in development and a hosted OpenAI-compatible
endpoint are interchangeable without touching the transport layer.
"""

__version__ = "1.0.0"
