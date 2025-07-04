import random
import time
from kubernetes import client, config, watch
config.load_kube_config()
v1 = client.CoreV1Api()
def get_schedulable_nodes():
    nodes = v1.list_node()
    node_names = [node.metadata.name for node in nodes.items]
    return node_names
def bind_pod(pod, node_name):
    target = client.V1ObjectReference(kind="Node", api_version="v1", name=node_name)
    meta = client.V1ObjectMeta(name=pod.metadata.name, namespace=pod.metadata.namespace)
    body = client.V1Binding(target=target, metadata=meta)
v1.create_namespaced_binding(namespace=pod.metadata.namespace, body=body)
    print(f"Scheduled pod {pod.metadata.name} to node {node_name}")
def main():
    w = watch.Watch()
    node_list = get_schedulable_nodes()
    for event in w.stream(v1.list_pod_for_all_namespaces, timeout_seconds=0):
        pod = event['object']
        if pod.status.phase == "Pending" and pod.spec.node_name is None:
            node = random.choice(node_list)
            try:
                bind_pod(pod, node)
            except Exception as e:
                print(f"Failed to schedule pod {pod.metadata.name}: {e}")
            time.sleep(1)
if _name_ == "_main_":
    main()
