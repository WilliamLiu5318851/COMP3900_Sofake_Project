from network import build_network
from prompts import agent_process_post

net = build_network(agents)
print(net.summary())
# seed story to hubs:
for hub in net.hubs.values():
    agent_process_post(hub, seed_post, ground_truth)
