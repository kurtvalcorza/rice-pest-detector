"""Rice black bug / white stemborer detector (RT-DETR) for light-trap images."""

__version__ = "0.1.0"

CLASS_NAMES: tuple[str, ...] = ("RBB_FEMALE", "RBB_MALE", "WSB_FEMALE", "WSB_MALE")
SPECIES_OF_CLASS: dict[int, str] = {0: "RBB", 1: "RBB", 2: "WSB", 3: "WSB"}
