# RL algorithm
from ray.rllib.algorithms.dqn.dqn import DQNConfig
import ray
# to use a custom env
from ray.tune.registry import register_env

# my custom env
from network_env import NetworkEnv
import numpy as np

# Just to suppress
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning) 

ray.init()

# registering my custom env with a name "netenv-v0" 
def env_creator(env_config):
    return NetworkEnv()

register_env('netenv-v0', env_creator)

replay_config = {
        "type": "MultiAgentPrioritizedReplayBuffer",
        "capacity": 60000,
        "prioritized_replay_alpha": 0.5,
        "prioritized_replay_beta": 0.5,
        "prioritized_replay_eps": 3e-6,
    }

# Set up RL 
config = (DQNConfig()
          .training(replay_buffer_config=replay_config)
          .environment(env='netenv-v0')
          .resources(num_gpus=0)
          .env_runners(num_env_runners=0, num_envs_per_env_runner=1)
        )
config.model["conv_filters"] = [
    [32, [3, 3], 1],  # 32 filters, 3x3 kernel, stride 1
    [64, [3, 3], 1],  # 64 filters, 3x3 kernel, stride 1
    [128, [3, 3], 1], # 128 filters, 3x3 kernel, stride 1
]

algo = config.build()

for _ in range(15):
    algo.train()