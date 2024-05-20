import networkx as nx
import numpy as np
import random
import sys
#import matplotlib.pyplot as plt

class Request:
    """This class represents a request. Each request is characterized by source and destination nodes and holding time (represented by an integer).

    The holding time of a request is the number of time slots for this request in the network. You should remove a request that exhausted its holding time.
    """
    counter = 0
    def __init__(self, s, t, ht):
        Request.counter += 1
        self.id = Request.counter
        self.s = s
        self.t = t
        self.ht = ht

    def __str__(self) -> str:
        return f'req({self.s}, {self.t}, {self.ht})'
    
    def __repr__(self) -> str:
        return self.__str__()
        
    def __hash__(self) -> int:
        # used by set()
        return self.id


class EdgeStats:
    """This class saves all state information of the system. In particular, the remaining capacity after request mapping and a list of mapped requests should be stored.
    """
    def __init__(self, u, v, cap) -> None:
        self.id = (u,v)
        self.u = u
        self.v = v 
        # remaining capacity
        self.cap = cap 

        # spectrum state (a list of requests, showing color <-> request mapping). Each index of this list represents a color
        self.__slots = [None] * cap
        # a list of the remaining holding times corresponding to the mapped requests
        self.__hts = [0] * cap
        # Link utilization data structure
        self.ut = []

    def __str__(self) -> str:
        return f'{self.id}, cap = {self.cap}: {self.reqs}'
    
    def add_request(self, req: Request, color:int):
        """update self.__slots by adding a request to the specific color slot

        Args:
            req (Request): a request
            color (int): a color to be used for the request
        """
        self.__slots[color] = req.__hash__()
        self.__hts[color] = req.ht

    def remove_requests(self):
        """update self.__slots by removing the leaving requests based on self.__hts; Also, self.__hts should be updated in this function.
        """
        for color in range(0, self.cap): 
            if (self.__hts[color] != None) and (self.__hts[color] > 0):
                self.__hts[color] = self.__hts[color] - 1
            
            if(self.__hts[color] == 0):
                self.__slots[color] = None

    def get_available_colors(self) -> list[int]:
        """return a list of integers available to accept requests
        """
        colorList = []
        for color in range(0, self.cap): 
            if(self.__hts[color] == 0 or self.__hts[color] == None):
                colorList.append(color)
        print(colorList)
        return colorList
    
    def show_spectrum_state(self):
        """Come up with a representation to show the utilization state of a link (by colors)
        """
        print("Link\tColor\tRequest\tHoldingTime")
        link = str(self.u)+'-'+str(self.v)
        for color in range(0, self.cap):
            print(f"{link}\t{str(color)}\t{str(self.__slots[color])}\t{str(self.__hts[color])}")

    def link_utilization(self):
        num_colors = 0
        for color in range(0, self.cap):
            if(self.__slots[color] != None):
                num_colors = num_colors+1
        
        self.ut.append(num_colors/self.cap)

    def episode_link_utilization(self):
        total_link_utilization = 0.0
        for ut in self.ut:
            total_link_utilization += ut
        total_link_utilization = total_link_utilization/len(self.ut)
        return total_link_utilization

def generate_requests(num_reqs: int, g: nx.Graph) -> list[Request]:
    """Generate a set of requests, given the number of requests and an optical network (topology)

    Args:
        num_reqs (int): the number of requests
        g (nx.Graph): network topology

    Returns:
        list[Request]: a list of request instances
    """
    min_ht = int(sys.argv[1])
    max_ht = int(sys.argv[2])
    reqList = []

    ht = random.choices(range(min_ht, max_ht), k=num_reqs)

    if len(sys.argv) > 4:
        src = int(sys.argv[3])
        dest = int(sys.argv[4])
        for num in range(0, num_reqs):
            req = Request(src, dest, ht[num])
            reqList.append(req)
    else:
        for num in range(0, num_reqs):
            s = random.randint(0, (g.number_of_nodes()-1))
            t = random.choice([i for i in range(0, g.number_of_nodes()) if i not in [s]])
            req = Request(s, t, ht[num])
            reqList.append(req)
            #print(s, " - ", t, " : ", ht[num])
    
    return reqList


def generate_graph() -> nx.Graph:
    """Generate a networkx graph instance importing a GML file. Set the capacity attribute to all links based on a random distribution.

    Returns:
        nx.Graph: a weighted graph
    """
    graph = nx.DiGraph(nx.read_gml('nsfnet.gml', label='id'))
    #print(graph.number_of_edges())
    #print(type(graph))
    #print(graph.number_of_nodes())
    #print(graph.nodes)
    #print(graph.edges())

    #nx.draw(graph, with_labels = True)
    #plt.show()

    return graph


def route(g: nx.Graph, estats: list[EdgeStats], req:Request, blocked_req:[]) -> list[EdgeStats]:
    """Use a routing algorithm to decide a mapping of requests onto a network topology. The results of mapping should be reflected. Consider available colors on links on a path. 

    Args:
        g (nx.Graph): a network topology
        req (Request): a request to map

    Returns:
        list[EdgeStats]: updated EdgeStats
    """

    print(req.s, " - ", req.t)
    path = nx.shortest_path(g, req.s, req.t, None, method='dijkstra')
    print("Path is : ", path)

    candidate_colors = []
    for index in range(0, len(path)-1):
        print(index, path[index])
        for stat in estats:
            if(stat.u == path[index] and stat.v == path[index+1]):
                candidate_colors.append(stat.get_available_colors())

    print(candidate_colors)
    if not blocked_req:
        reqs_blocked = 0
    else:
        reqs_blocked = blocked_req[-1]

    min_color = None
    for color in range(0, link_capacity):
        color_available_on_links = 0
        for index in range(0, len(candidate_colors)):
            if color not in candidate_colors[index]:
                break
            else:
                color_available_on_links = color_available_on_links + 1

        if color_available_on_links == len(candidate_colors):
            #print(color_available_on_links)
            min_color = color
            break

    print(min_color)

    if min_color != None:
        for index in range(0, len(path)-1):
            for stat in estats:
                if(stat.u == path[index] and stat.v == path[index+1]):
                    stat.add_request(req, min_color)
    else:
        reqs_blocked = reqs_blocked+1
        print("request is blocked")

    blocked_req.append(reqs_blocked)
    return estats

        
if __name__ == "__main__":
    num_requests = 100
    link_capacity = 10
    # 1. generate a network
    graph = generate_graph()
  
    #node_list = list(graph.nodes())
    
    # 2. generate a list of requests (num_reqs)
    # we simulate the sequential arrivals of the pre-generated requests using a for loop in this simulation
    requests = list()
    requests = generate_requests(num_requests, graph)
    blocked_requests = []

    # 3. prepare an EdgeStats instance for each edge.
    edgeStatsList = []
    for (u,v) in graph.edges:
        edgeStats = EdgeStats(u, v, link_capacity)
        edgeStatsList.append(edgeStats)

    # 4. this simulation follows the discrete event simulation concept. Each time slot is defined by an arrival of a request
    for req in requests:
        print(req.s, " - ", req.t, " : ", req.ht)
        # 4.1 use the route function to map the request onto the topology (update EdgeStats)
        edgeStatsList = route(graph, edgeStatsList, req, blocked_requests)

        # 4.2 remove all requests that exhausted their holding times (use remove_requests)
        for eStats in edgeStatsList:
            eStats.link_utilization()
            eStats.remove_requests()
        
        print("------------------------------")

    for eStats in edgeStatsList:
        print(eStats.u, eStats.v)
        for index in range(0, num_requests):
            print(eStats.ut[index])
        print("--------------------------------")
    
    print("Blocked Requests")
    for index in range(0, num_requests):
        print(blocked_requests[index])

    # Calculate link utilization for episode
    episode_network_utilization = 0.0
    for eStats in edgeStatsList:
        episode_network_utilization += eStats.episode_link_utilization()
    episode_network_utilization = episode_network_utilization/graph.number_of_edges()
    print("Network utilization : ", episode_network_utilization)
    #nx.draw(graph, with_labels = True)
    #plt.show()
