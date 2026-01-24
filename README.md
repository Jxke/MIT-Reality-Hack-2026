# Reality Hack - Meta Quest XR Application

A Unity-based XR application for Meta Quest devices featuring real-time face detection, spatial audio captioning, and adaptive gradient UI feedback.

## Features

- **TCP/Bluetooth Connectivity**: Connect to external devices for real-time data streaming
- **Face Detection**: Sentis-based face detection using passthrough camera
- **Spatial Captions**: Directional audio captions positioned in 3D space
- **Gradient UI Feedback**: Direction-based visual feedback with animated gradients
- **Light Effects**: Dynamic blinking light system for UI feedback
- **Input System**: Modern Unity Input System with Oculus integration

## Project Structure

```
Assets/
├── Scripts/
│   ├── SingularityManager.cs          # Main network & message handler
│   ├── TCPGradientUIController.cs     # Direction-based gradient activation
│   ├── CaptionManager.cs              # Caption positioning & display
│   ├── SentisObjectDetector.cs        # Face detection model
│   ├── LightBlink.cs                  # Blinking light control
│   └── CloseButton.cs                 # UI close button handler
├── Scenes/                            # Unity scenes
├── Settings/                          # Rendering & quality settings
├── TextMesh Pro/                      # TextMeshPro resources
└── Resources/                         # XR & OVR settings

ProjectSettings/                       # Unity project configuration
```

## Setup

### Requirements
- Unity 2022.3 LTS or newer
- Meta XR Plugin (OpenXR)
- Sentis (Neural Inference Engine)
- TextMeshPro

### Installation

1. Clone the repository
2. Open in Unity
3. Allow Unity to import all assets
4. Configure your device connection (TCP or Bluetooth) in `SingularityManager`

## Configuration

### Network Settings (SingularityManager)
- **Connection Type**: Choose between Wifi (TCP) or Bluetooth
- **Client IP**: Target device IP address (for TCP)
- **Client Port**: TCP port (default 7000)

### Face Detection (SentisObjectDetector)
- Assign your face detection model in the Inspector
- Assign labels file for detected classes
- Configure confidence threshold

### Captions (CaptionManager)
- Assign caption prefab
- Set caption lifetime and positioning

### Gradients (TCPGradientUIController)
- Assign left/right gradient images
- Configure fade duration and hold duration

## Message Protocol

The application receives messages in the format: `S<message>E\n`

### Direction Messages
- `1` - Front
- `2` - Back
- `3` - Left (activates left gradient)
- `4` - Right (activates right gradient)

### Text Messages
Any other text will be displayed as a spatial caption in the last received direction.

## Building

1. Go to File → Build Settings
2. Select Android as platform
3. Configure build settings
4. Click Build & Run

## Contributing

This is an MIT Reality Hack project. Contributions welcome!

## License

MIT License - See LICENSE file for details
