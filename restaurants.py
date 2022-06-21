import pandas as pd
from typing_extensions import TypeAlias
from typing import List, Any
from dataclasses import dataclass
from fuzzysearch import find_near_matches


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
    # picking 4326 epgs system.


Restaurants: TypeAlias = List[Restaurant]


def is_restaurant(name: Any, coord: Any, rest_id: Any, street: Any, tel: Any, neighbourhood: Any, district: Any,
                  street_num: Any) -> bool:
    """
    Checks that the given restaurant components are valid, i.e. they have proper types.
    Args:
        tel: presumed phone number of restaurant
        neighbourhood: presumed neighbourhood of the restaurant
        district: presumed district of the restaurant
        street_num: presumed street number of the restaurant (smallest one)
        street: presumed street of the restaurant
        coord: presumed coordinates of the restaurant
        rest_id: presumed id of the restaurant
        name: presumed name of the restaurant

    Returns:
        True if all the types of args match those of a restaurant, False otherwise.
    """
    return type(name) == str and type(rest_id) == str and type(coord) == list \
           and type(street[0]) == str and type(tel) == str and type(neighbourhood) == str and type(
        district) == str and type(street_num) == float


def is_match(query: str, r: Restaurant) -> bool:
    """
    Checks whether the user search query would match the specific restaurant, i.e. if
    there is some similitude between the restaurant fields and the query.
    Args:
        query: user input that will be compared to the restaurant
        r: restaurant that is being compared

    Returns:
    True if the restaurant matches the query, False otherwise.
    """
    return find_near_matches(query, r.name + r.street[0] + r.neighbourhood + r.street[0], max_l_dist=1) != []


def read() -> Restaurants:
    """
    Reads restaurants from the database.
    Returns:
    List of restaurants of the database, cleaned, i.e. no missing values, incorrect types
    """
    df = pd.read_csv("data/restaurants.csv")
    restaurants = []
    for rest in df.itertuples():
        rest_id = rest.register_id
        name = rest.name
        address = [rest.addresses_road_name, rest.addresses_road_id]
        coord = [rest.geo_epgs_4326_y, rest.geo_epgs_4326_x]  # epgs fromat is lat,long and we are using long,lat.
        tel = rest.values_value
        distr = rest.addresses_district_name
        nbr = rest.addresses_neighborhood_name
        str_num = rest.addresses_start_street_number
        r = Restaurant(rest_id, name, address, coord, str_num, distr, nbr, tel)
        if r not in restaurants and is_restaurant(name, coord, rest_id, address, tel, nbr, distr, str_num):
            restaurants.append(r)
    return restaurants


def find(query: str, restaurants: Restaurants) -> Restaurants:
    """
    Finds all restaurants from the database that relate to the query. See is_match to understand what similitude is.
    Args:
        query: user input that will be compared to the restaurants
        restaurants: list of all restaurants from the considered database.

    Returns:
    List of restaurants that match the query. Empty list if there are no similitudes whatsoever.
    """
    found: Restaurants = []
    for r in restaurants:
        if is_match(query, r) and len(found) != 10:
            found.append(r)
    return found
