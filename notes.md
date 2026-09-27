nvidia: 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
COMPOSIO_API_KEY=ak_TF4XSKIZ1-ZtzNohwA3P
npx skills add ComposioHQ/composio --skill composio -y



curl -X PATCH "http://localhost:7860/api/v1/flows/38239b65-e29b-496e-9fdf-919afca65257" \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk-9qf-8Dy2p-ntejdZWkAGxU8F2mf592HtMhzI29YJru8" \
  -d '{"mcp_enabled": true}'