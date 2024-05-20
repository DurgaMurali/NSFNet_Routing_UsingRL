import gymnasium as gym
from gymnasium import spaces
import numpy as np
import networkx as nx
import random
from sim import Request, EdgeStats

class NetworkEnv(gym.Env):
    def __init__(self) -> None:
        # create network
        self.graph = nx.DiGraph(nx.read_gml('nsfnet.gml', label='id'))
        self.num_nodes = self.graph.number_of_nodes()
        self.num_edges = self.graph.number_of_edges()
        self.num_requests = 100
        self.link_capacity = 10
        self.min_ht = 10
        self.max_ht = 20
        self.k_paths = 2
        self.round = 0
        self.total_reward = 0

        # define state space
        self.observation_space = spaces.Dict(
            {
                "req": spaces.Dict(
                    {
                        "s": spaces.Box(0, self.num_nodes-1, shape=(1,), dtype=int),
                        "t": spaces.Box(0, self.num_nodes-1, shape=(1,), dtype=int),
                        "ht": spaces.Box(self.min_ht, (self.max_ht-1), shape=(1,), dtype=int)
                    }
                ),
                "paths": spaces.Box(-1, self.num_nodes-1, shape=(self.k_paths, self.num_nodes), dtype=int),
                "edge_stats": spaces.Box(-1, (self.max_ht-1), shape=(self.link_capacity, self.num_nodes, self.num_nodes), dtype=int)
            }
        )

        self.action_space = spaces.Discrete(self.k_paths)

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.initialize_network_state()
        self.round = 0

        self.obs_req = {}
        self.generate_request()
        self.req = Request(self.obs_req["s"][0], self.obs_req["t"][0], self.ht[self.round])

        self.paths = np.zeros((self.k_paths, self.num_nodes), dtype=int)
        self.compute_simple_paths(self.obs_req["s"][0], self.obs_req["t"][0])

        self.edge_stats = np.zeros((self.link_capacity, self.num_nodes, self.num_nodes), dtype=int)
        for j in range(self.num_nodes):
            for k in range(self.num_nodes):
                if (j, k) in self.graph.edges:
                    for i in range(self.link_capacity):
                        self.edge_stats[i][j][k] = 0
                else:
                    for i in range(self.link_capacity):
                        self.edge_stats[i][j][k] = -1

        observation = self._get_obs()
        info = {}

        return observation, info

    def _get_obs(self):
        return {
            "req": self.obs_req,
            "paths": self.paths,
            "edge_stats": self.edge_stats
        }

    def step(self, action):
        self.round += 1
        blocking_reward = -1
        non_blocking_reward = 1
        incorrect_path_reward = -5
        terminated = (self.round == self.num_requests-1)

        action_path = self.paths[action]
        action_path = [i for i in action_path if i != -1]
        print(action_path)

        check_path_results = []
        non_blocking_path_exists = False
        for path in self.paths:
            path = [i for i in path if i != -1]
            if all(x == y for x, y in zip(path, action_path)) == False:
                # Check if choosing this path will be blocked
                check_path_results.append(self.track_network_state(path, True))

        for result in check_path_results:
            if result == True:
                non_blocking_path_exists = True

        req_blocked = False
        # check if correct path is selected   
        if len(action_path) > 0 and action_path[0] == self.obs_req["s"][0] and action_path[-1] == self.obs_req["t"][0]:
            req_blocked = self.track_network_state(action_path, False)
        else:
            # Incorrect path selected for the node pair
            reward = incorrect_path_reward

        # More than one non blocking paths exist
        if req_blocked == False and non_blocking_path_exists == True:
            reward = non_blocking_reward
        # Only selected path is non blocking
        elif req_blocked == False and non_blocking_path_exists == False:
            reward = non_blocking_reward * 2
        # Selected path blocks request and other non blocking paths exist
        elif req_blocked == True and non_blocking_path_exists == True:
            reward = blocking_reward * 2
        # No non blocking path exists
        elif req_blocked == True and non_blocking_path_exists == False:
            reward = 0

        self.total_reward += reward

        # generate new request
        self.generate_request()
        self.req = Request(self.obs_req["s"][0], self.obs_req["t"][0], self.ht[self.round])
        self.compute_simple_paths(self.obs_req["s"][0], self.obs_req["t"][0])

        observation = self._get_obs()
        info = {}

        # Calculate link utilization for episode
        episode_network_utilization = 0.0
        if terminated:
            for eStats in self.edgeStatsList:
                episode_network_utilization += eStats.episode_link_utilization()
            episode_network_utilization = episode_network_utilization/self.num_edges
            print("Network utilization : ", episode_network_utilization)
            print("Reward : ", self.total_reward)
            self.total_reward = 0

        return observation, reward, terminated, terminated, info
    
    def generate_request(self):
        '''s = random.randint(0, (self.num_nodes-1))
        t = random.choice([i for i in range(0, self.num_nodes) if i not in [s]])'''
        s = 1
        t = 7
        self.obs_req["s"] = np.array([s])
        self.obs_req["t"] = np.array([t])
        self.obs_req["ht"] = np.array([self.ht[self.round]])
        print("Req : ", s, t, self.ht[self.round])

    def initialize_network_state(self):
        self.ht = random.choices(range(self.min_ht, self.max_ht), k=self.num_requests)
        self.edgeStatsList = []
        for (u,v) in self.graph.edges:
            edgeStats = EdgeStats(u, v, self.link_capacity)
            self.edgeStatsList.append(edgeStats)

    def compute_simple_paths(self, u, v):
        simple_paths = nx.shortest_simple_paths(self.graph, u, v)
        index = 0
        self.paths.fill(0)
        for path in simple_paths:
            print(path)
            path_len = len(path)
            self.paths[index][:path_len] = path
            self.paths[index][path_len:] = -1
            index += 1
            if index == self.k_paths:
                break
        
        for i in range(index, self.k_paths):
            self.paths[i].fill(-1)

    def track_network_state(self, path, check_path):
        candidate_colors = []
        for index in range(0, len(path)-1):
            for stat in self.edgeStatsList:
                if(stat.u == path[index] and stat.v == path[index+1]):
                    candidate_colors.append(stat.get_available_colors())

        min_color = None
        for color in range(0, self.link_capacity):
            color_available_on_links = 0
            for index in range(0, len(candidate_colors)):
                if color not in candidate_colors[index]:
                    break
                else:
                    color_available_on_links = color_available_on_links + 1

            if color_available_on_links == len(candidate_colors):
                min_color = color
                break

        if min_color != None:
            blocked = False
        else:
            print("request is blocked")
            blocked = True
        
        if check_path == False:
            print(min_color)
            if blocked == False:
                for index in range(0, len(path)-1):
                    for stat in self.edgeStatsList:
                        if(stat.u == path[index] and stat.v == path[index+1]):
                            stat.add_request(self.req, min_color)

            for eStats in self.edgeStatsList:
                eStats.link_utilization()
                eStats.remove_requests()

            self.update_edge_stats(blocked, path, min_color)

        return blocked
    
    def update_edge_stats(self, blocked, action_path, min_color):
        # Update the holding time for the selected color for all the edges of the sleected path, if request not blocked
        if blocked == False:
            for index in range(len(action_path)-1):
                self.edge_stats[min_color][action_path[index]][action_path[index+1]] = self.req.ht

        for j in range(self.num_nodes):
            for k in range(self.num_nodes):
                for i in range(self.link_capacity):
                    if self.edge_stats[i][j][k] == -1:
                        break
                    elif self.edge_stats[i][j][k] > 0:
                        self.edge_stats[i][j][k] = self.edge_stats[i][j][k] - 1