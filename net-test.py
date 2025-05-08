from pyvis.network import Network
import json
 


net = Network(notebook=True, cdn_resources="remote")
net.add_node("A", label="Node A")
net.add_node("B", label="Node B")
net.add_node("C", label="Node C")
net.add_edge("A", "B")
net.add_edge("A", "C")
net.show("example.html")
