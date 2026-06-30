# LeRobot - LeKiwi Labs Edition (v0.5.1)

> **Note:** For the original Hugging Face LeRobot documentation, please refer to the [Original LeRobot Repository](https://github.com/huggingface/lerobot).

This repository is based on the **v0.5.1 tag** of the original [Hugging Face LeRobot](https://github.com/huggingface/lerobot) framework. The core functionality and code structure remain exactly the same as the upstream version. 

## What's Different?

The primary difference in this repository is the seamless integration of custom-developed modules from the `lekiwi_labs` repository. We have embedded custom components—including **leaders**, **teleoperators**, **cameras**, and **kinematics calibration**—to leverage the full power of the LeRobot framework for our specific hardware setups.

### Non-Intrusive Integration

Instead of modifying the core `lerobot` source code directly, our custom modules dynamically inject themselves into the Python path and override specific behaviors at runtime. 

#### 1. Dynamic Path Resolution
We dynamically add the project root and specific `lekiwi_labs` directories to the Python path. This allows us to cleanly import configurations and modules (such as UArm leader configs) without altering the core structure:

```python
import sys
from pathlib import Path

# Add project root and lerobot src to python path for importing
project_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(project_dir))

lerobot_src_dir = project_dir / "lerobot" / "src"
if lerobot_src_dir.exists():
    sys.path.append(str(lerobot_src_dir))

# Add uarm-leader-config1 directory to sys.path for importing uarm config and leader
uarm_leader_dir = project_dir / "lekiwi_labs" / "teleoperates" / "uarm-leader-config1"
sys.path.append(str(uarm_leader_dir))
```

#### 2. Custom Camera Modules
We integrate custom camera drivers, such as Grayscale OpenCV cameras, directly into the workflow:

```python
from lekiwi_labs.cameras.grayscale_opencv import GrayscaleOpenCVCamConfig  # noqa: F401
```

#### 3. Overriding Kinematics via `partialmethod`
To calibrate physical parameters like `wheel_radius` and `base_radius` for the LeKiwi robot, we override the default methods using `functools.partialmethod`. This ensures the original `lekiwi.py` remains untouched while giving us full control over the robot's speed and rotation mechanics:

```python
from functools import partialmethod
from lerobot.robots.lekiwi.lekiwi import LeKiwi

# Override LeKiwi kinematics parameters without modifying the original lekiwi.py script
WHEEL_RADIUS = 0.05  # default: 0.05 meters
BASE_RADIUS = 0.125  # default: 0.125 meters

LeKiwi._body_to_wheel_raw = partialmethod(  # type: ignore
    LeKiwi._body_to_wheel_raw,
    wheel_radius=WHEEL_RADIUS,
    base_radius=BASE_RADIUS,
)
LeKiwi._wheel_raw_to_body = partialmethod(  # type: ignore
    LeKiwi._wheel_raw_to_body,
    wheel_radius=WHEEL_RADIUS,
    base_radius=BASE_RADIUS,
)
```

By using these patterns, we maintain full compatibility with upstream LeRobot `v0.5.1` while unlocking tailored capabilities for `lekiwi_labs` hardware.
