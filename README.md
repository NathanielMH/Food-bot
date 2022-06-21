# MetroNyan


## Introduction

This page contains a description of our implementation of the project. With our code, a user can select a restaurant, and the bot will guide them to their destination.


## Prerequisites

In our implementation we used the standard libraries that were needed for the project, and they can be found in `requirements.txt`.


## Restaurants module

The restaurants `restaurants.py` module reads the data from the given file and turns it into a list of Restaurants. The `read` function takes care of that. Additionally, we added a function `is restaurant`, that makes sure that the data is valid by checking the types of the information that we are trying to save.

This module also deals with searches, that is, when a query is given, it searches through the list to find Restaurants that match that query. The `find` and `read` functions perform the search, and the `find` function returns a list of matches.

We created a data class for Restaurants:

```python3
@dataclass
class Restaurant:
    id: str
    name: str
    street: List  # name,id
    coordinates: List  # long,lat
    street_num: float
    district: str
    neighbourhood: str
    tel: str
 ```

This information will be shown to the user later in the bot module.


## Metro module

The metro module `metro.py` creates a graph of the Barcelona metro system, which is later used in the city module to create a graph of the entire city. This graph contains two types of nodes: Stations and Accesses, and the information for these is retreived from `estacions.csv` and `accessos.csv`.

We have created two data classes for these nodes:

```python3
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
```

There is an important disctinction within the Stations nodes. There are Stations that will have the same name, because they are physically located in the same station. However, in this project, a station only has one metro line, so when a station has more than one line (for example, Sants), we will create one Station node for each line that it contains.

There are also three types of edges. The edge that connects two nodes is called a Tram if both nodes are Stations and they are connected by a metro line, it is called a Link if both nodes are Stations, which are physically located within the same station (this means that there is a path within the station that connects them). Finally, an edge is called an Access if it connects a Station node with an Access node. The information saved for each edge is the following:

```python3
@dataclass
class Edge:
    type: str
    color: str
    distance: float
```

The main function in this module is the `get_metro_graph()`, which calls several other functions that we have implemented. The `read_stations()` and `read_accesses` functions retrieve the data from the files mentioned above and return lists of Stations and Accesses. These functions, in turn, call other funtions (`is_station` and `is_access`) to make sure that the data is clean. When reading the data, we add "Sta" at the front of the id's of Stations, and "A" in at the fromt of the id's of Accesses for more clarity.

After this, the `get_metro_graph` calls 3 different functions. The `add_stations()` function adds the Stations as nodes in the graph, and connects consecutive nodes of each metro line with Tram edges. Additionally, it returns a dictionary that groups all of the Stations by names, which will be used later to create the Link and Access edges.

The `add_accesses` function adds the Access nodes to the metro graph, and connects each access to its corresponding Station node (or nodes in the case where there are several Station nodes associated with the same station, as explained earlier). It does that by using the dictionary that we obtained earlier.

Finally, the `connect_stations` function also uses this dictionary to connect the Station nodes that are associated to the same physical station with Link edges.

The edges contain two important attributes: color and weight. The color of each edge is determined by its type by the `edge_to_color` function. If it is a metro Tram edge, its color is the color associated with its line. If it is an Access or a Link edge, it is black by default. Our function uses a dictionary that we implemented manually with the colors of each line. The weight attribute represents the time needed to travel between nodes. It is what we use later to find shortest paths, and it is determined by the `needed_time_h` function, which takes into account the distance between the nodes (computed using haversine) and the type of edge (the function has a fixed velocity for the metro as well as a fixed walking pace). The reason why the time is not contained as an attribute inside the Edge data class is because we need to use it as a parameter later for several networkx functions.




## City module

The city module creates a graph of Barcelona by merging two graphs: the metro graph obtained in the metro module, and the street graph of Barcelona.

First of all, the `get_osmnx_graph()` function retrieves the street graph. Because this process takes a while, the `save_osmnx_graph` and `load_osmnx_graph` are used to pickle the graph and save it and then retrieve it. Before saving the graph, the `clean_up_graph` function removes unnecessary information.

The main function of this module is the `build_city_graph` module, which merges the metro graph and the osmnx street graph. First, the `get_osmnx_nodes` adds the nodes from the street graph to the city graph (making sure that the data is clean and that the nodes have coordinates). Like we did in the metro module, we add "Str" at the beginning of the id's of every Street node for clarity. After that, the `get_osmnx` edges function adds the street graph edges, making sure that they are valid.

After adding the street graph, the function adds the metro graph. The `get_metro_nodes_and_links` function adds the metro nodes to the city graph. It also connects each Access node with the closest Street node. To do that, we use the function `ox.distance.nearest_nodes`. We need to call this function for every Access node, but the function is more efficient if we give it a list of nodes compared to when we call it seperately for each iteration. By doing this, we have to make the `get_metro_nodes_and_links` function longer; we need to define several auxiliary lists and dictionaries to be able to add the edges for each Access node later on. However, the 10 extra lines of code that we needed to add are compensated by the time gained (the function is executed in approximately 4 seconds compared to the 100 seconds it took when we called the `ox.distance.nearest_nodes` seperately for each access node).

Finally, the `build_city_graph` calls the `get_metro_edges` to add the edges from the metro graph to the city graph.

Building the city graph only needs to be done once, so, just like for the street graph, we decided to create 2 new functions: `save_city_graph` and `load_city_graph`. The first function pickles the graph and stores it in a file, and the second one loads the city graph so that it doesn't have to be created from scratch again. Building the city graph doesn't take a lot of time, so in our final version of this project we decided not to use these funcions (instead, every time the bot module is executed, it creates the city graph). However, it could also work by storing the city graph once and then loading it every time by using the functions we just mentioned.

Additionally, the city module includes the `find_path` and `plot_path` functions. The first function is used to find the shortes path between two given coordinates, and it calls the `nx.shortest_path` function, the second one generates a `.png` file of this path, which is then shown to the user. The `plot_path` function also uses an auxiliary function, `node_to_color`, which defines the color of each node (implemented manually with a dictionary).

The `time_from_path` function computes the estimated time in minutes that it will take the user to travel from one end of a given path to the other.

Finally, we have the `show` and `plot` functions, but these are used to check that the code is working correctly and aren't actually useful for the functionality of the project.


## Bot module

The bot module contains the code for the functions that our Telegram bot needs to preform. Those are: `\start`, `\help`, `\find`, `\info`, `\guide` and `\author`. Before calling any functions, however, we load the street graph and the city graph generated by the city module, as these are needed for several of the functions (we have pickled the city graph as well as the street graph to make the process faster).

The `where` function is used to store the user's location when they share it. While the coordinates are usually expressed as (latitude, longitude), networkx uses (longitude, latitude), so that is how we have defined our coordinates.

The `\find` function reads a query from the user, and calls the restaurants module to find restaurants that match the query. If none are found, or if the query is empty, the bot sends an error message. Otherwise, the command gives a user a list of restaurants (the `build_restaurants_list` is called to build a structured list for the user).

The `\info` command takes a number from the restaurants given in the `\find` list, and calls the `restaurant_info`, which again calls the restaurant module to find the information for that given restaurant. The function returns an error if the user asks for a number outside the range of the list, or if the `\find` command has not been executed.

Finally, the `\guide` command takes a number from the restaurants given in the `\find` list and calls the `find_path` and `plot_path` functions in the city module. It then gives the user the obtained image so that they have directions to get to the restaurant, as well as an estimated time computed by `time_from_path`. The function returns an error message if the user hasn't shared their location or asks for an invalid restaurant.


## Authors

Nathaniel Mitrani and Paula Esquerrà
