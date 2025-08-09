CREATE OR REPLACE FUNCTION validate_prompt_schema(messages JSONB) RETURNS BOOLEAN AS $$
DECLARE
  schema CONSTANT JSONB := '{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "type": {
        "enum": [
          "chatml",
          "string"
        ]
      }
    },
    "allOf": [
      {
        "if": {
          "properties": {
            "type": {
              "const": "string"
            }
          }
        },
        "then": {
          "required": [
            "string"
          ],
          "properties": {
            "string": {
              "type": "string"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "type": {
              "const": "chatml"
            }
          }
        },
        "then": {
          "required": [
            "messages"
          ],
          "properties": {
            "messages": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["role", "content"],
                "properties": {
                  "role": {
                    "enum": [
                      "system",
                      "user",
                      "assistant"
                    ]
                  },
                  "content": {
                    "oneOf": [
                      {
                        "type": "string"
                      },
                      {
                        "type": "array",
                        "items": {
                          "oneOf": [
                            {
                              "type": "object",
                              "properties": {
                                "type": {
                                  "const": "text"
                                },
                                "text": {
                                  "type": "string"
                                }
                              },
                              "required": ["type", "text"]
                            },
                            {
                              "type": "object",
                              "properties": {
                                "type": {
                                  "const": "image_url"
                                },
                                "image_url": {
                                  "type": "string",
                                  "format": "uri"
                                }
                              },
                              "required": ["type", "image_url"]
                            }
                          ]
                        }
                      }
                    ]
                  }
                }
              }
            }
          }
        }
      }
    ]
  }'::JSONB;

BEGIN
  RETURN jsonb_matches_schema(schema::json, messages);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

ALTER TABLE public.llms
ADD CONSTRAINT check_prompt CHECK (validate_prompt_schema(prompt));


CREATE OR REPLACE FUNCTION validate_completion_schema(messages JSONB) RETURNS BOOLEAN AS $$
DECLARE
  schema CONSTANT JSONB := '{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
      "type": {
        "enum": [
          "chatml",
          "string"
        ]
      }
    },
    "allOf": [
      {
        "if": {
          "properties": {
            "type": {
              "const": "string"
            }
          }
        },
        "then": {
          "required": [
            "string"
          ],
          "properties": {
            "string": {
              "type": "string"
            }
          }
        }
      },
      {
        "if": {
          "properties": {
            "type": {
              "const": "chatml"
            }
          }
        },
        "then": {
          "required": [
            "messages"
          ],
          "properties": {
            "messages": {
              "type": "object",
              "properties": {
                "role": {
                "type": "string",
                "const": "assistant"
              },
                "content": {
                  "type": "string"
                }
              },
              "required": ["role", "content"]
            }
          }
        }
      }
    ]
}'::JSONB;

BEGIN
  RETURN jsonb_matches_schema(schema::json, messages);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

ALTER TABLE public.llms
ADD CONSTRAINT check_completion CHECK (validate_completion_schema(completion));

