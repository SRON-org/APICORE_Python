from __future__ import annotations

import json
import timeit

from apicore import loads

SAMPLE = json.dumps(
    {
        "friendly_name": "Benchmark API",
        "link": "https://api.example.com/generate",
        "func": "POST",
        "APICORE_version": "2.0",
        "configs": {
            "request": {
                "headers": {
                    "Authorization": "Bearer {{parameters.api_key}}",
                },
                "timeout_ms": 30000,
            }
        },
        "parameters": [
            {
                "name": "api_key",
                "type": "string",
                "required": True,
                "friendly_name": "API Key",
                "value": "",
                "text_secret": True,
            },
            {
                "name": "prompt",
                "type": "string",
                "required": True,
                "friendly_name": "Prompt",
                "value": "cat",
            },
        ],
        "handlers": {
            "200": {"action": "response"},
            "default": {"action": "return"},
        },
        "response": {
            "image": {
                "content_type": "URL",
                "path": "data.outputs[0].url",
            }
        },
    }
)


def main() -> None:
    loops = 10_000
    seconds = timeit.timeit(lambda: loads(SAMPLE), number=loops)
    print(f"Parsed {loops} documents in {seconds:.3f}s ({loops / seconds:.0f} docs/s)")


if __name__ == "__main__":
    main()
