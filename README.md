# Strands Sonnet 5 smoke test

A single Strands agent calls the project-mapped `global.anthropic.claude-sonnet-5` through an AIR Studio External Agent Model Proxy. The FastAPI service listens on port 8080 and has a multiplication tool.

Put the contents of this directory at the root of the branch used by AIR Studio’s **Deploy from code**. Set both the container port and the service port to `8080`. Configure these environment variables at runtime.

| Variable | Value |
| --- | --- |
| `AIR_MODEL_PROXY_URL` | The HTTPS **Model Proxy Endpoint URL** from the registered External Agent. Use the base URL shown by AIR. |
| `AIR_MODEL_PROXY_TOKEN` | The credential approved for that AIR proxy, provided through the runtime’s secret store. |
| `AIR_MODEL_PROXY_AUTH` | `bearer` for the `Authorization: Bearer` header or `air_api_key` for `AIR-Api-Key`. Confirm the method with the AIR deployment administrator. |

The client uses the Bedrock Converse request format against the AIR proxy. AIR authenticates the request and handles provider access for the mapped model. Keep credentials out of Git, the image, and test payloads.

Run these checks from a network that can reach the service.

```sh
curl -fsS "$SERVICE_URL/ping"
curl -fsS "$SERVICE_URL/invocations" \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Use the multiply tool to calculate 25 times 4.","streaming":false}'
```

The first check confirms that the HTTP service is up and reports whether the proxy environment variables were set. The second should return a response containing `100`, the model ID and `multiply_used: true`. The deployed pod sends a `Converse` request when `streaming` is false, and a `ConverseStream` request otherwise.

[Strands Bedrock model configuration](https://strandsagents.com/docs/user-guide/sdk/model-providers/amazon-bedrock/).
