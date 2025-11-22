# Veridian Client SDK

The official Python client for the Veridian AI Safety Platform.

## Installation

```bash
pip install veridian-client
```

## Usage

Initialize the client with your API key:

```python
from veridian import Veridian

client = Veridian(api_key="your-api-key")
```

### Features

- **Check Prompt**: Verify if an inbound user prompt is safe.
  ```python
  result = client.check_prompt("Is this safe?")
  ```

- **Check Output**: Verify if an outbound agent response is safe.
  ```python
  result = client.check_output("Generated response")
  ```

- **Log Action**: Log and check an agent tool call.
  ```python
  result = client.log_action("tool_name", "tool_args")
  ```

- **Run Red Team**: Trigger a red team campaign.
  ```python
  result = client.run_redteam("user_intent", "target_description")
  ```
