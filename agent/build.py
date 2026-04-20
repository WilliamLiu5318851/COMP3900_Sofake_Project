from network import *

<<<<<<< HEAD
=======


>>>>>>> 38f534055f8ff4e0f502eb618b161348e87d13df
net = build_network(agents)
print(net.summary())
# seed story to hubs:
for hub in net.hubs.values():
    agent_process_post(hub, seed_post, ground_truth)