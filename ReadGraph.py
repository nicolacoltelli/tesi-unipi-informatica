import networkx
import matplotlib.pyplot as plt
from matplotlib.pyplot import text
from networkx.drawing.nx_agraph import graphviz_layout

EDGES = True

graph = networkx.read_gpickle("fig.pkl")
filtered_graph = networkx.Graph()

for node in graph.nodes:

	valid_edges_count = 0
	edges_to_draw = []

	for edge in graph.edges(node, data=True):

		if (edge[2]['len'] < 50):
			valid_edges_count+=1

			edges_to_draw.append(edge)

	if (valid_edges_count >= 2):
		for edge in edges_to_draw:
			attributes = edge[2].copy()
			del attributes["len"]
			filtered_graph.add_edge(edge[0], edge[1])
			filtered_graph[edge[0]][edge[1]].update(attributes)


pos = graphviz_layout(filtered_graph)
networkx.draw_networkx_nodes(filtered_graph, pos, node_color="orange")
if (EDGES == True):
	networkx.draw_networkx_edges(filtered_graph, pos)
	networkx.draw_networkx_edge_labels(filtered_graph, pos, font_size=5, rotate=False)
for node, (x, y) in pos.items():
	text(x, y, node, fontsize=8, ha='center', va='center', clip_on=True)
plt.show()
