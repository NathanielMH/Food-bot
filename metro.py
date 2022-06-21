import pandas as pd
from typing import List, Tuple, Dict, Any #type: ignore
from dataclasses import dataclass #type: ignore
import networkx #type: ignore
from haversine import haversine #type: ignore
import matplotlib.pyplot as plt #type: ignore
from typing_extensions import TypeAlias
from staticmap import StaticMap, CircleMarker, Line #type: ignore


@dataclass
class Station:
    name: str
    line: str
    order: int
    pos: Tuple[float, float]
    id: int


@dataclass
class Access:
    name: str
    accessibility: bool
    station_name: str
    pos: Tuple[float, float]
    id: int


@dataclass
class Edge:
    type: str
    color: str
    distance: float


Stations: TypeAlias = List[Station]

Accesses: TypeAlias = List[Access]

MetroGraph: TypeAlias = networkx.Graph

Coord: TypeAlias = Tuple[float, float]  # (longitude, latitude)


def is_station(name: Any, line: Any, order: Any, pos: Any, station_id: Any) -> bool:
    """
    Checks that the given station components are valid, i.e. they have proper types.
    Args:
        name: presumed name of the station
        line: presumed line of the station
        order: presumed order of the station
        pos: presumed pos of the station
        station_id: presumed id of the station

    Returns:
    True if all the types of args match those of a station, False otherwise.
    """
    return type(name) == str and type(line) == str and type(order) == int and type(pos) == tuple and type(station_id) == int


def is_access(name: Any, accessibility: Any, station_name: Any, pos: Any, access_id: Any) -> bool:
    """
    Checks that the given access components are valid, i.e. they have proper types.
    Args:
        access_id: presumed access id
        name: presumed name of the access
        accessibility: presumed accessibility of the access
        station_name: presumed name of the station that is accessible from the given access
        pos: presumed position of the access
        id: presumed id of the access

    Returns:
    True if all the types of args match those of an access, False otherwise.
    """
    return type(name) == str and type(station_name) == str and type(accessibility) == bool and type(
        pos) == Tuple and type(access_id) == int


def edge_to_color(edge_info: str) -> str:
    """
    Returns the color associated to the given edge, considering metro lines as Tram types and other edge types.
    This is done thanks to the info obtained from:
    https://www.tmb.cat/es/transporte-barcelona/mapa/metro
    Last updated: 16/05/22
    Args:
        edge_info: edge type

    Returns:
    String with the color as accepted by the networkx and osmnx libraries, not in Hex or RGB.
    """
    e_to_c = {"L1": "red", "L2": "purple", "L3": "green",
              "L4": "yellow", "L5": "blue", "L9S": "orange", "L9N": "orange", "L10S": "lightblue",
              "L10N": "lightblue", "Street": "black", "Acces": "black", "Link": "black", "L11": "green",
              "FM": "darkgreen"}
    return e_to_c[edge_info]


def needed_time_h(p1: Coord, p2: Coord, method: str) -> float:
    """
    Returns the given time in hours that is needed to go from p1 to p2 by the method given.
    Args:
        p1: coordinates of the src
        p2: coordinates of the dst
        method: way of transportation considered (either "walk" or "metro" are implemented for now)

    Returns:
    Float with the time in hours needed to go from p1 to p2 using method.
    """
    m = method
    t_delay: float = 0
    if m == "acces" or m == "link":
        t_delay = 0.05
        m = "walk"
    method_to_speed = {"walk": 5, "metro": 30}
    # This dictionary can be scaled once we implement new ways of transportation in the project.
    # Speed in km/h for method can also be changed
    # t_delay is the time delay in hours to go from an access to the street, or from time needed to use a link.
    speed = method_to_speed[m]
    return haversine(p1, p2) / speed + t_delay


def read_stations() -> Stations:
    """
    Reads cleaned stations from database, i.e. removing missing values, incomplete and incorrect stations.
    Returns:
    List of stations present in the database.
    """
    df = pd.read_csv("data/estacions.csv")
    stations = []
    for station in df.itertuples():
        name = station.NOM_ESTACIO
        line = station.NOM_LINIA
        order = station.ORDRE_ESTACIO
        station_id = station.CODI_ESTACIO_LINIA
        point = station.GEOMETRY[7:-1]
        pos = (float(point.split(' ')[0]), float(point.split(' ')[1]))
        if is_station(name, line, order, pos, station_id):
            stations.append(Station(name, line, order, pos, station_id))
    return stations


def read_accesses() -> Accesses:
    """
    Reads cleaned accesses from database, i.e. removing missing values, incomplete and incorrect accesses.
    Returns:
    List of accesses present in the database.
    """
    df = pd.read_csv("data/accessos.csv")
    accesses = []
    for access in df.itertuples():
        name = access.NOM_ACCES
        id_accessibility = access.ID_TIPUS_ACCESSIBILITAT
        accessibility = (id_accessibility == 1)
        point = access.GEOMETRY[7:-1]
        pos = (float(point.split(' ')[0]), float(point.split(' ')[1]))
        station_name = access.NOM_ESTACIO
        access_id = access.CODI_ACCES
        accesses.append(Access(name, accessibility, station_name, pos, access_id))
    return accesses


def add_stations(stations: Stations, metro: MetroGraph) -> Dict:
    """
    Adds the stations to the metro graph.
    Args:
        stations: list of stations in the database
        metro: graph with metro lines being built

    Returns:
    Returns a dictionary that has station names as keys and a list of stations accessible from the given station (key).
    """
    prev_station = None
    access_to_stations: Dict[str, Stations] = {}
    for station in stations:
        metro.add_node(station.id, info=station,
                       pos=station.pos, type="Station")
        if prev_station is not None and prev_station.line == station.line:
            metro.add_edge(station.id, prev_station.id, info=Edge("Tram", edge_to_color(station.line),
                                                                  haversine(station.pos, prev_station.pos)),
                           weight=needed_time_h(station.pos, prev_station.pos, "metro"))
        prev_station = station
        if station.name in access_to_stations.keys():
            access_to_stations[station.name] += [station]
        else:
            access_to_stations[station.name] = [station]
    return access_to_stations


def add_accesses(accesses: List, access_to_stations: Dict, metro: MetroGraph) -> None:
    """
    Adds accesses to the metro graph.
    Args:
        accesses: list of accesses from the database
        access_to_stations: dictionary, station.name as keys and list of stations accessible from it as values
        metro: metro graph
    """
    for access in accesses:
        metro.add_node(access.id, info=access, pos=access.pos, type="Acces")
        station_name = access.station_name
        connections = access_to_stations[station_name]
        for station in connections:
            metro.add_edge(access.id, station.id,
                           info=Edge("Acces", edge_to_color("Acces"), haversine(access.pos, station.pos)),
                           weight=needed_time_h(access.pos, station.pos, "acces"))


def connect_stations(access_to_stations: Dict, metro: MetroGraph) -> None:
    """
    Connects the different metro stations between them using the access_to_stations dictionary built in add_stations.
    Args:
        access_to_stations: dictionary, station.name as keys and list of stations accessible from it as values
        metro: metro graph
    """
    for station_name in access_to_stations.keys():
        list_stations = access_to_stations[station_name]
        n = len(list_stations)
        for i in range(n - 1):
            for j in range(i + 1, n):
                metro.add_edge(list_stations[i].id, list_stations[j].id,
                               info=Edge("Link", edge_to_color("Link"),
                                         haversine(list_stations[i].pos, list_stations[j].pos)),
                               weight=needed_time_h(list_stations[i].pos, list_stations[j].pos, "link"))


def get_metro_graph() -> MetroGraph:
    """
    Builds the metro graph from scratch. Uses read_stations, read_accesses, add_stations, add_accesses
    and connect stations.
    Returns:
    MetroGraph with the information from the given databases. See functions aforementioned.
    """
    metro = MetroGraph()
    stations = read_stations()
    accesses = read_accesses()
    access_to_stations = add_stations(stations, metro)
    add_accesses(accesses, access_to_stations, metro)
    connect_stations(access_to_stations, metro)
    return metro


def metro_show(g: MetroGraph) -> None:
    """
    Shows MetroGraph on screen.
    Args:
        g: MetroGraph being drawn
    """
    networkx.draw(g, with_labels=False, node_size=25,
            pos=networkx.get_node_attributes(g, "pos"))
    plt.show()


def metro_plot(g: MetroGraph, filename: str) -> None:
    """
    Plots the MetroGraph into a map and saves it in the path: filename.png
    Args:
        g: MetroGraph to be saved
        filename: determines path where image is saved
    Note: The file is saved as filename.png, if you can't open .png extensions consider an online converter.
    """
    new_map = StaticMap(500, 500)
    for node in g.nodes():
        new_map.add_marker(CircleMarker((g.nodes[node]['pos']), 'red', 3))
    for edge in g.edges():
        new_map.add_line(
            Line([g.nodes[edge[0]]['pos'], g.nodes[edge[1]]['pos']], 'blue', 3))
    image = new_map.render()
    image.save(filename + ".png")