// Inference contract shared with rice_pest_detector/infer.py and docs/inference-contract.md.
// Change these only together with the Python reference.

/// The contract default. A model may declare another square input size in its manifest (RF-DETR-M: 576).
const int inputSize = 640;
const double defaultThreshold = 0.5;

/// The detector drops scores below this before counting, so every counting threshold must sit above it.
const double detectorFloor = 0.02;
const int numQueries = 300;
const List<String> classNames = ['RBB_FEMALE', 'RBB_MALE', 'WSB_FEMALE', 'WSB_MALE'];

/// The app reports species only: two of the four sex classes miss the 0.70 mAP50 gate.
const Map<int, String> speciesOfClass = {0: 'RBB', 1: 'RBB', 2: 'WSB', 3: 'WSB'};

const String inputName = 'pixel_values';
const String logitsName = 'logits';
const String boxesName = 'pred_boxes';
