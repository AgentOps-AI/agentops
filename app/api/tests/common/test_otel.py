from agentops.common.otel import otel_attributes_to_nested


class TestOtelAttributesToNested:
    """Tests for the otel_attributes_to_nested function."""

    def test_simple_nested_attributes(self):
        """Test basic nested attribute conversion."""
        attributes = {"foo.bar": "value1", "foo.baz": "value2", "top": "level"}

        result = otel_attributes_to_nested(attributes)

        assert result == {"foo": {"bar": "value1", "baz": "value2"}, "top": "level"}

    def test_array_attributes(self):
        """Test conversion of attributes with numeric indices to arrays."""
        attributes = {
            "items.0.name": "first",
            "items.0.value": "100",
            "items.1.name": "second",
            "items.1.value": "200",
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {"items": [{"name": "first", "value": "100"}, {"name": "second", "value": "200"}]}

    def test_mixed_nested_and_arrays(self):
        """Test complex structure with both nested objects and arrays."""
        attributes = {
            "user.name": "John",
            "user.tags.0": "admin",
            "user.tags.1": "developer",
            "user.metadata.age": "30",
            "user.metadata.city": "NYC",
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {
            "user": {"name": "John", "tags": ["admin", "developer"], "metadata": {"age": "30", "city": "NYC"}}
        }

    def test_sparse_array(self):
        """Test that sparse arrays are filled with None values."""
        attributes = {"array.0": "first", "array.5": "sixth"}

        result = otel_attributes_to_nested(attributes)

        assert result == {"array": ["first", None, None, None, None, "sixth"]}

    def test_string_terminal_value_skip(self):
        """Test that we skip attributes when trying to set a key on a string value."""
        attributes = {
            "field": "string_value",
            "field.subfield": "should_be_skipped",  # Can't add subfield to a string
            "field.another.deep": "also_skipped",
        }

        result = otel_attributes_to_nested(attributes)

        # Only the first string value should be set
        assert result == {"field": "string_value"}

    def test_type_mismatch_string_key_on_list(self):
        """Test that string keys on lists are skipped."""
        attributes = {
            "field.0": "array_item",
            "field.invalid": "should_be_skipped",  # String key on what should be a list
        }

        result = otel_attributes_to_nested(attributes)

        # Only the valid array item should be set
        assert result == {"field": ["array_item"]}

    def test_type_mismatch_int_key_on_dict(self):
        """Test that integer keys on dicts are skipped."""
        attributes = {
            "field.name": "dict_value",
            "field.0": "should_be_skipped",  # Integer key on what should be a dict
        }

        result = otel_attributes_to_nested(attributes)

        # Only the valid dict entry should be set
        assert result == {"field": {"name": "dict_value"}}

    def test_deep_nesting(self):
        """Test deeply nested structures."""
        attributes = {"a.b.c.d.e.f": "deep_value", "a.b.c.d.e.g": "another_deep", "a.b.x": "sibling"}

        result = otel_attributes_to_nested(attributes)

        assert result == {
            "a": {"b": {"c": {"d": {"e": {"f": "deep_value", "g": "another_deep"}}}, "x": "sibling"}}
        }

    def test_legacy_gen_ai_prompt_conversion(self):
        """Test that legacy gen_ai.prompt string format is converted to indexed format."""
        attributes = {"gen_ai.prompt": "What is the weather today?", "gen_ai.model": "gpt-4"}

        result = otel_attributes_to_nested(attributes)

        assert result == {
            "gen_ai": {
                "prompt": [{"content": "What is the weather today?", "role": "user"}],
                "model": "gpt-4",
            }
        }

    def test_indexed_gen_ai_prompt_not_converted(self):
        """Test that properly indexed gen_ai.prompt is not modified."""
        attributes = {
            "gen_ai.prompt.0.content": "Hello",
            "gen_ai.prompt.0.role": "user",
            "gen_ai.prompt.1.content": "Hi there!",
            "gen_ai.prompt.1.role": "assistant",
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {
            "gen_ai": {
                "prompt": [
                    {"content": "Hello", "role": "user"},
                    {"content": "Hi there!", "role": "assistant"},
                ]
            }
        }

    def test_gen_ai_non_string_prompt_not_converted(self):
        """Test that gen_ai.prompt that's already an object/array is not converted."""
        # First, let's build a structure where gen_ai.prompt is already an array
        attributes = {"gen_ai.prompt.0": "already_indexed"}

        result = otel_attributes_to_nested(attributes)

        # Should not apply legacy conversion since it's already indexed
        assert result == {"gen_ai": {"prompt": ["already_indexed"]}}

    def test_empty_attributes(self):
        """Test that empty attributes dict returns empty result."""
        result = otel_attributes_to_nested({})
        assert result == {}

    def test_single_level_attributes(self):
        """Test attributes with no nesting."""
        attributes = {"field1": "value1", "field2": "value2", "field3": "value3"}

        result = otel_attributes_to_nested(attributes)

        assert result == attributes

    def test_numeric_string_keys_not_converted(self):
        """Test that numeric strings that aren't at array positions stay as strings."""
        attributes = {
            "map.123": "value",  # This should create a dict with string key "123"
            "array.0": "item",  # This should create an array
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {"map": {"123": "value"}, "array": ["item"]}

    def test_conflicting_paths_first_wins(self):
        """Test that when paths conflict, the first one processed wins."""
        attributes = {
            "field.sub": "string_value",
            "field.sub.nested": "should_be_skipped",  # Can't nest under string
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {"field": {"sub": "string_value"}}

    def test_complex_real_world_example(self):
        """Test a complex real-world example with OpenTelemetry span attributes."""
        attributes = {
            "gen_ai.prompt.0.content": "Write a function",
            "gen_ai.prompt.0.role": "user",
            "gen_ai.completion.0.content": "def hello(): pass",
            "gen_ai.completion.0.role": "assistant",
            "gen_ai.model": "gpt-4",
            "gen_ai.usage.prompt_tokens": "10",
            "gen_ai.usage.completion_tokens": "5",
            "llm.is_streaming": "false",
            "span.kind": "CLIENT",
            "error.message": "none",
            "tags.0": "production",
            "tags.1": "v2",
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {
            "gen_ai": {
                "prompt": [{"content": "Write a function", "role": "user"}],
                "completion": [{"content": "def hello(): pass", "role": "assistant"}],
                "model": "gpt-4",
                "usage": {"prompt_tokens": "10", "completion_tokens": "5"},
            },
            "llm": {"is_streaming": "false"},
            "span": {"kind": "CLIENT"},
            "error": {"message": "none"},
            "tags": ["production", "v2"],
        }

    def test_edge_case_existing_string_in_path(self):
        """Test handling when trying to traverse through an existing string value."""
        attributes = {
            "a.b": "string",
            "a.b.c.d": "should_skip",  # Can't traverse through string at a.b
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {"a": {"b": "string"}}

    def test_multiple_legacy_prompts(self):
        """Test multiple gen_ai attributes with legacy format."""
        attributes = {
            "gen_ai.prompt": "User question here",
            "gen_ai.completion": "AI response here",  # This won't be converted, only prompt
            "other.field": "value",
        }

        result = otel_attributes_to_nested(attributes)

        assert result == {
            "gen_ai": {
                "prompt": [{"content": "User question here", "role": "user"}],
                "completion": "AI response here",  # Not converted
            },
            "other": {"field": "value"},
        }
