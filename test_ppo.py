# RL algorithm
from ray.rllib.algorithms.ppo import PPOConfig
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

# Set up RL 
config = (PPOConfig()
          .training(gamma=0.9, lr=0.001, lambda_=0.99)
          .environment(env='netenv-v0')
          .resources(num_gpus=0)
          .env_runners(num_env_runners=0, num_envs_per_env_runner=1)
        )
config.model["conv_filters"] = [
    [32, [3, 3], 1],  # 32 filters, 3x3 kernel, stride 1
    [64, [3, 3], 1],  # 64 filters, 3x3 kernel, stride 1
    [128, [3, 3], 1], # 128 filters, 3x3 kernel, stride 1
]
#config.model["conv_activation"] = "relu"  # Activation function

algo = config.build()

for _ in range(15):
    algo.train()