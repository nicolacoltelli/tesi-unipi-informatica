import networkx
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout

graph = networkx.read_gpickle("fig.pkl")
pos = graphviz_layout(graph)
networkx.draw_networkx_nodes(graph,pos)
networkx.draw_networkx_labels(graph,pos)
plt.show()