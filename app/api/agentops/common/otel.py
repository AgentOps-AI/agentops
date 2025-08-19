from typing import Any


def _is_array_index(key: str) -> bool:
    """Check if a key represents an array index."""
    return key.isdigit()


def _migrate_legacy_gen_ai_prompt(result: dict) -> None:
    """Handle legacy OpenAI agents format migration in-place."""
    if 'gen_ai' in result and isinstance(result['gen_ai'], dict):
        if 'prompt' in result['gen_ai'] and isinstance(result['gen_ai']['prompt'], str):
            # Convert legacy format to indexed format
            legacy_prompt = result['gen_ai']['prompt']
            result['gen_ai']['prompt'] = [
                {
                    'content': legacy_prompt,
                    'role': 'user',  # Default role for legacy data
                }
            ]


def otel_attributes_to_nested(attributes: dict[str, str]) -> dict[str, Any]:
    """
    Convert OTEL attributes from a flat dictionary to a nested dictionary suitable
    for JSON serialization.

    'foo.bar.0.baz': 'value' -> {'foo': {'bar': [{'baz': 'value'}]}}
    """
    result = {}

    for path, value in attributes.items():
        keys = path.split('.')
        current = result

        # Navigate to the correct position
        for i, key in enumerate(keys[:-1]):  # All keys except the last
            next_key = keys[i + 1]

            # Skip if we hit a string value (can't traverse into it)
            if isinstance(current, str):
                break

            if isinstance(current, list):
                # Current is a list, key must be numeric
                if not _is_array_index(key):
                    break  # Type mismatch: string key on list

                key_int = int(key)
                # Extend list if needed
                while len(current) <= key_int:
                    # Determine what to append based on next key
                    if _is_array_index(next_key):
                        current.append([])
                    else:
                        current.append({})
                current = current[key_int]

            elif isinstance(current, dict):
                # Skip small numeric keys (0-9) on dicts as they likely indicate array indices
                if _is_array_index(key) and int(key) < 10:
                    break  # Type mismatch: numeric index on dict

                if key not in current:
                    # Create new structure based on next key
                    if next_key == "0":  # Specifically "0" suggests array start
                        current[key] = []
                    else:
                        current[key] = {}

                # Skip if the existing value is a string
                if isinstance(current[key], str):
                    break

                current = current[key]
            else:
                break  # Unexpected type

        else:  # No break occurred, we can set the final value
            final_key = keys[-1]

            # Skip if current is a string
            if isinstance(current, str):
                continue

            if isinstance(current, list):
                # Current is a list, final key must be numeric
                if not _is_array_index(final_key):
                    continue  # Type mismatch

                key_int = int(final_key)
                while len(current) <= key_int:
                    current.append(None)
                current[key_int] = value

            elif isinstance(current, dict):
                # Skip small numeric keys on dicts
                if _is_array_index(final_key) and int(final_key) < 10:
                    continue  # Type mismatch
                current[final_key] = value

    # Apply legacy format migrations
    _migrate_legacy_gen_ai_prompt(result)

    return result
