import random
import time
from kubernetes import client, config, watch

config.load_kube_config()
v1 = client.CoreV1Api()

nodes = []
q_table = {}
alpha = 0.1
gamma = 0.9
epsilon = 0.2

def get_schedulable_nodes():
    node_list = v1.list_node()
    return [node.metadata.name for node in node_list.items]

def get_state(pod):
    try:
        for c in pod.spec.containers:
            if c.resources.requests and "cpu" in c.resources.requests:
                cpu_str = c.resources.requests["cpu"]
                cpu = int(float(cpu_str.replace("m","")) if "m" in cpu_str else float(cpu_str)*1000)
                return cpu // 100
    except:
        pass
    return 1

def choose_node(state):
    if state not in q_table:
        q_table[state] = {node: 0.0 for node in nodes}
    if random.uniform(0,1) < epsilon:
        return random.choice(nodes)
    else:
        return max(q_table[state], key=q_table[state].get)

def update_q(state, action, reward, next_state):
    old_value = q_table[state][action]
    future_max = max(q_table.get(next_state, {n:0 for n in nodes}).values())
    new_value = old_value + alpha * (reward + gamma * future_max - old_value)
    q_table[state][action] = new_value

def bind_pod(pod, node_name):
    target = client.V1ObjectReference(kind="Node", api_version="v1", name=node_name)
    meta = client.V1ObjectMeta(name=pod.metadata.name, namespace=pod.metadata.namespace)
    body = client.V1Binding(target=target, metadata=meta)
    v1.create_namespaced_binding(namespace=pod.metadata.namespace, body=body)
    print(f"Scheduled pod {pod.metadata.name} to node {node_name}")

def main():
    global nodes
    nodes = get_schedulable_nodes()
    w = watch.Watch()
    for event in w.stream(v1.list_pod_for_all_namespaces, timeout_seconds=0):
        pod = event['object']
        if pod.status.phase == "Pending" and pod.spec.node_name is None:
            state = get_state(pod)
            action = choose_node(state)
            try:
                bind_pod(pod, action)
                reward = 1
            except Exception as e:
                print(f"Failed to schedule pod {pod.metadata.name}: {e}")
                reward = -1
            next_state = state
            update_q(state, action, reward, next_state)
            time.sleep(1)

if _name_ == "_main_":
    main()
