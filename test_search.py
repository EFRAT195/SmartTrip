from agent import run_agent

result = run_agent(
    region="ירושלים",
    category="טבע",
    hours=4,
    budget=100
)

print("AGENT RESULT:")
print(result["result"])

print("\nAGENT ACTIONS:")
for log in result["logs"]:
    print(log)