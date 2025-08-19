curl -X POST http://localhost:4318/v1/traces \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer $(cat .jwt)" \
 -d "$(cat <<EOF
{
   "resourceSpans": [{
     "resource": {
       "attributes": []
     },
     "scopeSpans": [{
       "spans": [{
         "name": "test-span",
         "traceId": "$(head -c 16 /dev/urandom | hexdump -ve '1/1 "%.2x"')",
         "spanId": "$(head -c 8 /dev/urandom | hexdump -ve '1/1 "%.2x"')",
         "kind": 1,
         "startTimeUnixNano": $(date +%s)000000000,
         "endTimeUnixNano": $(date +%s)100000000,
         "attributes": [{
           "key": "gen_ai.response.model",
           "value": {"stringValue": "gpt-4"}
         }, {
            "key": "gen_ai.usage.prompt_tokens",
            "value": {"intValue": 100}
         }, {
            "key": "gen_ai.usage.completion_tokens",
            "value": {"intValue": 1000}
         }]
       }]
     }]
   }]
}
EOF
)"