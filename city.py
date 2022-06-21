from typing import List, Tuple, Union #type: ignore
import osmnx as ox #type: ignore
import os #type: ignore
import haversine #type: ignore
import networkx
import pickle as pck
from typing import Union
import haversine
import osmnx as ox

from metro import *

CityGraph: TypeAlias = networkx.Graph

OsmnxGraph: TypeAlias = networkx.MultiDiGraph

NodeID: TypeAlias = Union[int, str]

Path: TypeAlias = List[NodeID]


def node_to_color(node_info: str) -> str:
    """
    Gives the color associated to node in terms of its type.
    Args:
        node_info: node type
    Returns:
    String with color, respecting osmnx and networkx colors,  not Hex or RGB.
    """
    n_to_c = {"Station": "red", "Acces": "brown", "Street": "green"}
    return n_to_c[node_info]


def get_osmnx_graph() -> OsmnxGraph:
    """
    Fetches Barcelona graph from osmnx and simplifies it.
    Warning: can take a while.
    Returns:
    OsmnxGraph of Barcelona.
    """
    return ox.graph_from_place('Barcelona', network_type='walk', simplify=True)


def clean_up_graph(g: OsmnxGraph) -> OsmnxGraph:
    """
    Cleans up the graph of some information, in this case its geometry (if present) irrelevant for the project.
    Args:
        g: OsmnxGraph
    Returns:
    OsmnxGraph without geometry information in edges.
    """
    for u, v, key, geom in g.edges(data="geometry", keys=True):
        if geom is not None:
            del (g[u][v][key]["geometry"])
    return g


def save_city_graph(g: CityGraph, filename: str) -> None:
    """
    Pickles city graph in path filename.pickle to avoid generating it everytime,
    if the pickle doesn't exist already.
    Args:
        g: CityGraph to be pickled
        filename: name of the file to save it
    """
    if not os.path.exists(filename + '.pickle'):
        pck_out = open(filename + ".pickle", "wb")
        pck.dump(g, pck_out)
        pck_out.close()


def load_city_graph(filename: str) -> CityGraph:
    """
    Loads the CityGraph from path filename.pickle, read only.
    Args:
        filename: name of the file where the CityGraph is
    Returns:
    CityGraph of Barcelona
    """
    pck_in = open(filename + ".pickle", "rb")
    return pck.load(pck_in)


def save_osmnx_graph(g: OsmnxGraph, filename: str) -> None:
    """
    Pickles osmnx graph in path filename.pickle to avoid loading it everytime from osmnx,
    if the pickle doesn't exist already.
    Args:
        g: Osmnxgraph to be pickled
        filename: name of the file to save it
    """
    g = clean_up_graph(g)
    if not os.path.exists(filename + ".pickle"):
        pck_out = open(filename + ".pickle", "wb")
        pck.dump(g, pck_out)
        pck_out.close()


def load_osmnx_graph(filename: str) -> OsmnxGraph:
    """
    Loads the CityGraph from path filename.pickle, read only.
    Args:
        filename: name of the file where the CityGraph is
    Returns:
    OsmnxGraph of Barcelona
    """
    pck_in = open(filename + ".pickle", "rb")
    return pck.load(pck_in)


def get_osmnx_edges(g1: OsmnxGraph, g: CityGraph) -> None:
    """
    Adds Osmnx edges to CityGraph.
    Args:
        g1: OsmnxGraph
        g: CityGraph
    """
    for edge in g1.edges():
        node1 = edge[0]
        node2 = edge[1]
        if edge[0] != edge[1]:
            g.add_edge(node1, node2,
                       info=Edge("Street", edge_to_color("Street"),
                                 haversine(g.nodes[node1]['pos'], g.nodes[node2]['pos'])),
                       weight=needed_time_h(g.nodes[node1]['pos'], g.nodes[node2]['pos'], "walk"))


def get_osmnx_nodes(g1: OsmnxGraph, g: CityGraph) -> None:
    """
    Adds OsmnxGraph nodes to CityGraph
    Args:
        g1: OsmnxGraph
        g: CityGraph to be modified
    """
    for node in g1.nodes():
        if 'x' in g1.nodes[node] and 'y' in g1.nodes[node]:
            g.add_node(node, pos=[g1.nodes[node]['x'],
                                  g1.nodes[node]['y']], type="Street")


def get_metro_edges(g2: MetroGraph, g: CityGraph) -> None:
    """
    Adds metro edges to CityGraph.
    Args:
        g2: MetroGraph
        g: CityGraph to be modified
    """
    for edge in g2.edges():
        g.add_edge(edge[0], edge[1], info=g2.edges[edge]
        ['info'], weight=g2.edges[edge]['weight'])


def get_metro_nodes_and_links(g1: OsmnxGraph, g2: MetroGraph, g: CityGraph) -> None:
    """
    Adds metro nodes to CityGraph, as well as edges for links between accesses and stations.
    Args:
        g1: OsmnxGraph
        g2: MetroGraph
        g: CityGraph to be modified
    """
    node_access: List = []
    dict_access: List[Dict] = []
    coord_access_lat: List[float] = []
    coord_access_long: List[float] = []
    for node in g2.nodes():
        # Adding nodes from MetroGraph:
        g.add_node(node, pos=g2.nodes[node]['pos'],
                   type=g2.nodes[node]['type'])
        if g2.nodes[node]['type'] == "Acces":
            node_access.append(node)
            coord_access_long.append(g2.nodes[node]['pos'][0])
            coord_access_lat.append(g2.nodes[node]['pos'][1])
    nearest_to_access = ox.distance.nearest_nodes(
        g1, coord_access_long, coord_access_lat, return_dist=False)
    for i in range(len(node_access)):
        dict_access.append({'info': Edge("Street", edge_to_color("Street"),
                                         haversine(g.nodes[node_access[i]]['pos'],
                                                   g.nodes[nearest_to_access[i]]['pos'])),
                            'weight': needed_time_h(g.nodes[node_access[i]]['pos'],
                                                    g.nodes[nearest_to_access[i]]['pos'], "walk")})
    # Adding edges from accesses to their respective stations:
    # merges lists into a list of tuples.
    list_of_edges = list(zip(node_access, nearest_to_access, dict_access))
    g.add_edges_from(list_of_edges)
    # This configuration allows the efficient execution of nearest_nodes by giving it a list of coordinates.


def build_city_graph(g1: OsmnxGraph, g2: MetroGraph) -> CityGraph:
    """
    Builds the CityGraph from the OsmnxGraph and Metro.
    Args:
        g1: OsmnxGraph
        g2: MetroGraph
    Returns:
    CityGraph given from union of both given graphs.
    """
    g = CityGraph()
    get_osmnx_nodes(g1, g)
    get_osmnx_edges(g1, g)
    get_metro_nodes_and_links(g1, g2, g)
    get_metro_edges(g2, g)
    return g


def time_from_path(g: CityGraph, p: Path) -> int:
    """
    Gives the time needed to complete a certain path.
    Args:
        g: CityGraph of the city
        p: path from which we are computing the time needed to complete
    Returns:
    Int with the amount of minutes needed to complete the given path in the graph g
    """
    total_time = 0
    for i in range(len(p) - 1):
        total_time += g.edges[p[i], p[i + 1]]['weight'] * 60
    total_time = int(total_time)
    return total_time


def find_path(ox_g: OsmnxGraph, g: CityGraph, src: Coord, dst: Coord) -> Path:
    """
    Returns the shortest path from src to dst as a list of nodes.
    Args:
        ox_g: OsmnxGraph
        g: CityGraph
        src: starting point of path
        dst: end point of path
    Returns:
    Path, list of nodes from src to dst.
    """
    origin = ox.distance.nearest_nodes(ox_g, src[0], src[1], return_dist=False)
    destination = ox.distance.nearest_nodes(
        ox_g, dst[0], dst[1], return_dist=False)
    path = networkx.shortest_path(g, origin, destination)
    return path


def show(g: CityGraph) -> None:
    """
    Shows the CityGraph in an interactive form in a new window
    Args:
        g: CityGraph
    """
    networkx.draw(g, with_labels=False, node_size=25,
                  pos=networkx.get_node_attributes(g, "pos"))
    plt.show()


def plot(g: CityGraph, filename: str) -> None:
    """
    Plots CityGraph in path filename.png.
    Args:
        g: CityGraph to be plotted
        filename: name of the file to save plot
    Note: The file is saved as filename.png, if you can't open .png extensions consider an online converter.
    """
    # stores g as an image with the city map in the background in the filename file
    new_map = StaticMap(1000, 1000)
    for node in g.nodes():
        color = node_to_color(g.nodes[node]['type'])
        new_map.add_marker(CircleMarker((g.nodes[node]['pos']), color, 1))
    for edge in g.edges():
        color = g.edges[edge]['info'].color
        new_map.add_line(
            Line([g.nodes[edge[0]]['pos'], g.nodes[edge[1]]['pos']], color, 1))
    if os.path.exists(filename + ".png"):
        os.remove(filename + ".png")
    image = new_map.render()
    image.save(filename + ".png")


def plot_path(g: CityGraph, p: Path, filename: str) -> None:
    """
    Plots path and saves it in path filename.png, as a StaticMap.
    Args:
        g: CityGraph to be drawn over
        p: path to be plotted
        filename: name of the file to save plot
    Note: The file is saved as filename.png, if you can't open .png extensions consider an online converter.
    """
    new_map = StaticMap(1000, 1000)
    for i in range(len(p)):
        color = node_to_color(g.nodes[p[i]]['type'])
        new_map.add_marker(CircleMarker((g.nodes[p[i]]['pos']), color, 2))
    for i in range(len(p) - 1):
        color = g.edges[p[i], p[i + 1]]['info'].color
        new_map.add_line(
            Line([g.nodes[p[i]]['pos'], g.nodes[p[i + 1]]['pos']], color, 3))
    image = new_map.render()
    image.save(filename + ".png")
