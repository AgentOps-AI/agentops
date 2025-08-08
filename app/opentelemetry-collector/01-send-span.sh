curl -X POST http://localhost:4318/v1/traces \
 -H "Content-Type: application/json" \
 -H "Authorization: Bearer $(cat .jwt)" \
 -d '{
   "resourceSpans": [{
     "resource": {
       "attributes": [{
         "key": "ProjectId",
         "value": {"stringValue": "1c0ffdac-e7f7-494d-93f9-cac955f25de8"}
       }]
     },
     "scopeSpans": [{
       "spans": [{
         "name": "test-span",
         "traceId": "01020304050607080102030405060708",
         "spanId": "0102030405060708",
         "kind": 1,
         "startTimeUnixNano": "1644004200000000000",
         "endTimeUnixNano": "1644004300000000000"
       }]
     }]
   }]
 }'
