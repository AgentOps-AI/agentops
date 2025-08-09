-- Add the indexes
SELECT 
        TraceId, 
        Timestamp as timestamp,
        StatusCode as status_code, 
        ifNull(SpanAttributes['gen_ai.usage.prompt_tokens'], 0) as prompt_tokens,
        ifNull(SpanAttributes['gen_ai.usage.completion_tokens'], 0) as completion_tokens,
        ifNull(SpanAttributes['gen_ai.usage.total_tokens'], 0) as total_tokens,
        ifNull(SpanAttributes['gen_ai.request.model'], '') as request_model,
        ifNull(SpanAttributes['gen_ai.response.model'], '') as response_model,
        ifNull(SpanAttributes['gen_ai.llm.model'], '') as gen_ai_llm_model,
        ifNull(SpanAttributes['llm.model'], '') as llm_model,
        ifNull(SpanAttributes['gen_ai.system'], '') as system
    FROM otel_traces
    WHERE (project_id = '6183afc9-5fc8-47a0-b1c4-a4d589d0866e')
    ORDER BY Timestamp ASC
    

    SELECT 
        min(if(Duration > 0, Duration, null)) as min_duration,
        max(if(Duration > 0, Duration, null)) as max_duration,
        avg(if(Duration > 0, Duration, null)) as avg_duration,
        sum(if(Duration > 0, Duration, null)) as total_duration,
        count() as span_count,
        count(DISTINCT TraceId) as trace_count
    FROM otel_traces
    WHERE (project_id = '6183afc9-5fc8-47a0-b1c4-a4d589d0866e')
    

    SELECT 
        TraceId,
        sum(Duration) as trace_duration
    FROM otel_traces
    WHERE (project_id = '6183afc9-5fc8-47a0-b1c4-a4d589d0866e')
    GROUP BY TraceId
    ORDER BY trace_duration ASC
