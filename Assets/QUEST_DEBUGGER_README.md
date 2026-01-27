# Quest Debugger Setup Guide

## Overview
The Quest Debugger provides easy testing of the Reality Hack application directly on the Meta Quest headset without needing network connectivity.

## Components

### 1. QuestDebugger Script
Main debugger script that handles controller input and microphone testing.

**Button Mappings:**
- **A Button (Right Hand)** → Sends Direction 1 (Front)
- **B Button (Right Hand)** → Sends Direction 2 (Back)
- **X Button (Left Hand)** → Sends Direction 3 (Left)
- **Y Button (Left Hand)** → Sends Direction 4 (Right)
- **Grip Button (Either Hand)** → Toggle Microphone Recording

### 2. MicrophoneAnalyzer Script
Analyzes audio input and generates test captions based on detected sounds.

**Features:**
- Loudness detection
- Frequency analysis
- Automatic caption suggestions based on audio characteristics
- Low/mid/high frequency classification

## Setup Instructions

1. **Add QuestDebugger to Scene**
   - Create an empty GameObject in your scene
   - Add the `QuestDebugger` script component
   - Assign the SingularityManager reference

2. **Add MicrophoneAnalyzer (Optional)**
   - Create another empty GameObject
   - Add the `MicrophoneAnalyzer` script component
   - Customize audio response thresholds

3. **Enable Microphone Permissions**
   - The app already has microphone permissions in AndroidManifest.xml
   - They will be requested at runtime

## Usage

### Testing Direction System
1. Put on the Quest headset
2. Press A/B/X/Y buttons in sequence
3. Watch the UI respond to each direction
4. Check the on-screen debug panel for confirmation

### Testing Caption System
1. Press Grip button to start microphone recording
2. Speak into the microphone for up to 5 seconds
3. Release and the audio will be analyzed
4. A caption based on detected audio will appear

### Debug UI Panel
The on-screen panel shows:
- Button control reference
- Microphone recording status
- Real-time debug log
- Audio loudness levels

## Customization

### Change Button Mappings
Edit the button assignments in `QuestDebugger.HandleButtonInput()`:
```csharp
if (OVRInput.GetDown(OVRInput.Button.One)) // A button
```

Available buttons:
- `OVRInput.Button.One` - A (Right)
- `OVRInput.Button.Two` - B (Right)
- `OVRInput.Button.Three` - X (Left)
- `OVRInput.Button.Four` - Y (Left)
- `OVRInput.Button.PrimaryHandTrigger` - Grip
- `OVRInput.Button.SecondaryHandTrigger` - Index Trigger

### Adjust Microphone Settings
In the Inspector, modify:
- **Sample Rate**: Audio capture quality (default 16000 Hz)
- **Recording Duration**: Max length per recording (default 5 seconds)
- **Silence Threshold**: Minimum loudness to detect speech (default 0.01)

### Customize Audio Responses
Edit `MicrophoneAnalyzer.cs` to change caption suggestions:
```csharp
public string[] highFrequencyHints = new string[] { ... };
public string[] normalFrequencyHints = new string[] { ... };
```

## Troubleshooting

### Microphone Not Working
- Ensure microphone permissions are granted
- Check that `enableMicrophoneDebug` is true
- Verify `Microphone.devices.Length > 0`

### Buttons Not Responding
- Ensure QuestDebugger script is active
- Verify SingularityManager reference is assigned
- Check that SingularityManager is in the scene

### No Debug UI Visible
- Set `showDebugUI = true` in Inspector
- Ensure the script is running (not disabled)
- Check canvas/camera setup

## Advanced Usage

### Manual Caption Testing
Call from another script:
```csharp
questDebugger.TestSendCaption("Custom caption text");
```

### Frequency Band Analysis
Access raw frequency data:
```csharp
float[] bands = microphoneAnalyzer.GetFrequencyBands();
```

## Integration with SingularityManager

The debugger bypasses network connectivity and directly calls:
- `singularityManager.sendMessage(directionNumber.ToString())` for directions
- `singularityManager.sendMessage(captionText)` for captions

This allows full testing of the caption and direction system without external hardware.

## Performance Notes

- Debug UI draws every frame but has minimal impact
- Microphone recording is CPU efficient
- Frequency analysis uses simple band splitting (not FFT for performance)

## Future Enhancements

- Voice command recognition
- Gesture support
- Real-time frequency visualization
- Multiple language support
- Custom caption templates
