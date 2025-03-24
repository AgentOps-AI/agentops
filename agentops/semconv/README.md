# OpenTelemetry Semantic Conventions for Generative AI Systems

## General GenAI Attributes
| Attribute                                  | Type    |
|--------------------------------------------|---------|
| `gen_ai.agent.description`                 | string  |
| `gen_ai.agent.id`                          | string  |
| `gen_ai.agent.name`                        | string  |
| `gen_ai.operation.name`                    | string  |
| `gen_ai.output.type`                       | string  |
| `gen_ai.request.choice.count`              | int     |
| `gen_ai.request.encoding_formats`          | string[]|
| `gen_ai.request.frequency_penalty`         | double  |
| `gen_ai.request.max_tokens`                | int     |
| `gen_ai.request.model`                     | string  |
| `gen_ai.request.presence_penalty`          | double  |
| `gen_ai.request.seed`                      | int     |
| `gen_ai.request.stop_sequences`            | string[]|
| `gen_ai.request.temperature`               | double  |
| `gen_ai.request.top_k`                     | double  |
| `gen_ai.request.top_p`                     | double  |
| `gen_ai.response.finish_reasons`           | string[]|
| `gen_ai.response.id`                       | string  |
| `gen_ai.response.model`                    | string  |
| `gen_ai.system`                            | string  |
| `gen_ai.token.type`                        | string  |
| `gen_ai.tool.call.id`                      | string  |
| `gen_ai.tool.name`                         | string  |
| `gen_ai.tool.type`                         | string  |
| `gen_ai.usage.input_tokens`                | int     |
| `gen_ai.usage.output_tokens`               | int     |

## OpenAI-Specific Attributes
| Attribute                                  | Type    |
|--------------------------------------------|---------|
| `gen_ai.openai.request.service_tier`       | string  |
| `gen_ai.openai.response.service_tier`      | string  |
| `gen_ai.openai.response.system_fingerprint`| string  |

## GenAI Event Attributes

### Event: `gen_ai.system.message`
| Attribute                                  | Type    |
|--------------------------------------------|---------|
| `gen_ai.system`                            | string  |

#### Body Fields
| Attribute                                  | Type    |
|--------------------------------------------|---------|
| `content`                                  | string  |
| `role`                                     | string  |

### Event: `gen_ai.user.message`
| Attribute                                  | Type    |
|--------------------------------------------|---------|
| `gen_ai.system`                            | string  |