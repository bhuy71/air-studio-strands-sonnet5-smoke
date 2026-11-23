# Strands Sonnet 5 smoke test

A single Strands agent uses the Amazon Bedrock global inference profile `global.anthropic.claude-sonnet-5`. The FastAPI service listens on port 8080 and has a single multiplication tool.

Set the container port and service port to `8080` in AIR Studio. The pod needs an AWS workload identity authorized to invoke the Bedrock profile, including streaming. Set `AWS_REGION` for a source region other than `us-east-1`. The sample calls Bedrock directly.

From a network that reaches the service, check `GET /ping` and then `POST /invocations` with `{"prompt":"Use the multiply tool to calculate 25 times 4."}`. The successful invocation should return `100`, the model ID and `multiply_used: true`.

[AWS sample using Sonnet 5](https://github.com/aws-samples/sample-agentcore-behavioral-contract-evaluations) · [Strands Bedrock provider](https://strandsagents.com/docs/user-guide/sdk/model-providers/amazon-bedrock/)
