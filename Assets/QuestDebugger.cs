using UnityEngine;
using System.Collections;

namespace Sngty
{
    public class QuestDebugger : MonoBehaviour
    {
        [Header("References")]
        public SingularityManager singularityManager;

        [Header("Microphone Settings")]
        public bool enableMicrophoneDebug = true;
        public int microphoneSampleRate = 16000;
        public float recordingDuration = 5f;
        public float silenceThreshold = 0.001f;

        [Header("Speech Recognition")]
        public bool useSpeechToText = true;

        [Header("UI")]
        public bool showDebugUI = true;
        private string debugLog = "";
        private string lastCapturedText = "";
        private string currentDirection = "None";

        private AudioClip recordingClip;
        private bool isRecording = false;
        private float recordingTimer = 0f;
        private AndroidJavaObject speechRecognizer;

        void Awake()
        {
            if (singularityManager == null)
            {
                singularityManager = FindObjectOfType<SingularityManager>();
            }

            Debug.Log("Quest Debugger initialized - Press A/B/X/Y for directions, Grip to toggle mic");
        }

        void Update()
        {
            HandleButtonInput();
            UpdateMicrophoneRecording();
        }

        void HandleButtonInput()
        {
            // Right hand buttons
            if (OVRInput.GetDown(OVRInput.Button.One)) // A button
            {
                SendDirection(1, "Front");
            }
            if (OVRInput.GetDown(OVRInput.Button.Two)) // B button
            {
                SendDirection(2, "Back");
            }

            // Left hand buttons
            if (OVRInput.GetDown(OVRInput.Button.Three)) // X button
            {
                SendDirection(3, "Left");
            }
            if (OVRInput.GetDown(OVRInput.Button.Four)) // Y button
            {
                SendDirection(4, "Right");
            }

            // Grip buttons to toggle microphone
            if (OVRInput.GetDown(OVRInput.Button.PrimaryHandTrigger))
            {
                ToggleMicrophone();
            }
        }

        void SendDirection(int directionNumber, string directionName)
        {
            if (singularityManager != null)
            {
                Debug.Log($"[QuestDebugger] Sending direction: {directionNumber} ({directionName})");
                currentDirection = directionName;
                singularityManager.ProcessMessage(directionNumber.ToString());
                LogDebug($"[DIRECTION] Button pressed: {directionName} ({directionNumber})");
                
                // Verify gradient controller received it
                if (singularityManager.tCPGradientUIController != null)
                {
                    Debug.Log($"[QuestDebugger] Gradient controller exists, should activate gradients");
                }
                else
                {
                    Debug.LogError("[QuestDebugger] Gradient controller is NULL!");
                }
            }
            else
            {
                LogDebug($"[ERROR] SingularityManager is null!");
                Debug.LogError("[QuestDebugger] SingularityManager is NULL!");
            }
        }

        void ToggleMicrophone()
        {
            if (!enableMicrophoneDebug)
                return;

            isRecording = !isRecording;

            if (isRecording)
            {
                StartMicrophoneRecording();
                LogDebug("[MIC] Recording started...");
            }
            else
            {
                StopMicrophoneRecording();
            }
        }

        void StartMicrophoneRecording()
        {
            try
            {
                string[] devices = Microphone.devices;
                
                if (devices.Length == 0)
                {
                    LogDebug("[MIC ERROR] No microphone devices found!");
                    isRecording = false;
                    return;
                }

                string deviceName = devices[0];
                LogDebug($"[MIC] Using device: {deviceName}");

                recordingClip = Microphone.Start(deviceName, false, (int)recordingDuration, microphoneSampleRate);
                recordingTimer = 0f;
                isRecording = true;
            }
            catch (System.Exception e)
            {
                LogDebug($"[MIC ERROR] {e.Message}");
                isRecording = false;
            }
        }

        void StopMicrophoneRecording()
        {
            try
            {
                if (Microphone.IsRecording(""))
                {
                    Microphone.End("");
                }

                if (recordingClip != null)
                {
                    ProcessAudioClip(recordingClip);
                }

                isRecording = false;
                LogDebug("[MIC] Recording stopped");
            }
            catch (System.Exception e)
            {
                LogDebug($"[MIC ERROR] {e.Message}");
            }
        }

        void UpdateMicrophoneRecording()
        {
            if (!isRecording)
                return;

            recordingTimer += Time.deltaTime;

            if (recordingTimer >= recordingDuration)
            {
                StopMicrophoneRecording();
            }
        }

        void ProcessAudioClip(AudioClip clip)
        {
            if (clip == null)
            {
                LogDebug("[MIC] No audio clip to process");
                Debug.LogError("[ProcessAudio] clip is NULL");
                return;
            }

            Debug.Log($"[ProcessAudio] Clip length: {clip.length}s, samples: {clip.samples}, channels: {clip.channels}");

            // Get audio data
            float[] samples = new float[clip.samples * clip.channels];
            clip.GetData(samples, 0);

            // Calculate average loudness
            float loudness = 0f;
            foreach (float sample in samples)
            {
                loudness += Mathf.Abs(sample);
            }
            loudness /= samples.Length;

            LogDebug($"[MIC] Audio loudness: {loudness:F6}");
            Debug.Log($"[ProcessAudio] Loudness: {loudness:F6}, Threshold: {silenceThreshold:F6}, Above threshold: {loudness > silenceThreshold}");

            // Check if there's meaningful audio
            if (loudness > silenceThreshold)
            {
                LogDebug("[MIC] Audio detected! Processing speech...");
                Debug.Log("[ProcessAudio] Audio level above threshold, processing");
                
                if (useSpeechToText)
                {
                    // Use Android speech recognition
                    StartCoroutine(RecognizeSpeech(clip));
                }
                else
                {
                    // Fallback: just show audio level with "Speech detected"
                    SendCaption($"[Speech Detected - Level: {loudness:F2}]");
                }
            }
            else
            {
                LogDebug($"[MIC] Silence detected (loudness {loudness:F6} < threshold {silenceThreshold:F6})");
                Debug.Log($"[ProcessAudio] Audio level too low: {loudness:F6}");
            }
        }

        IEnumerator RecognizeSpeech(AudioClip clip)
        {
            try
            {
                Debug.Log("[Speech] Starting speech recognition...");
                
                // Use Android's native speech recognizer
                using (AndroidJavaClass unityPlayer = new AndroidJavaClass("com.unity3d.player.UnityPlayer"))
                {
                    AndroidJavaObject activity = unityPlayer.GetStatic<AndroidJavaObject>("currentActivity");
                    
                    using (AndroidJavaClass intentClass = new AndroidJavaClass("android.content.Intent"))
                    {
                        AndroidJavaObject intent = new AndroidJavaObject("android.content.Intent");
                        intent.Call<AndroidJavaObject>("setAction", intentClass.GetStatic<string>("ACTION_RECOGNIZE_SPEECH"));
                        intent.Call<AndroidJavaObject>("putExtra", "android.speech.extra.LANGUAGE_MODEL", 
                            intentClass.GetStatic<string>("EXTRA_LANGUAGE_MODEL"));
                        
                        // Start speech recognition
                        activity.Call("startActivityForResult", intent, 1);
                        Debug.Log("[Speech] Activity started");
                    }
                }
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"[Speech] Android speech recognition not available: {e.Message}");
                Debug.Log("[Speech] Falling back to simple detection...");
                SendCaption("[Speech Detected - STT unavailable]");
            }

            yield return null;
        }

        void SendCaption(string text)
        {
            // Only show captions if direction is Front (1)
            if (currentDirection != "Front")
            {
                Debug.Log($"[Caption] Skipping caption - direction is {currentDirection}, not Front");
                LogDebug($"[CAPTION SKIPPED] Direction is {currentDirection}, not Front");
                return;
            }

            if (singularityManager != null)
            {
                lastCapturedText = text;
                Debug.Log($"[SendCaption] Sending caption: {text}");
                singularityManager.ProcessMessage(text);
                LogDebug($"[CAPTION] {text}");
            }
            else
            {
                Debug.LogError("[SendCaption] singularityManager is null!");
            }
        }

        public void HandleSpeechResult(string recognizedText)
        {
            Debug.Log($"[Speech] Result: {recognizedText}");
            SendCaption(recognizedText);
        }

        void LogDebug(string message)
        {
            Debug.Log(message);
            debugLog += message + "\n";

            // Keep only last 10 lines
            string[] lines = debugLog.Split('\n');
            if (lines.Length > 10)
            {
                debugLog = string.Join("\n", lines, lines.Length - 10, 10);
            }
        }

        void OnGUI()
        {
            if (!showDebugUI)
                return;

            GUILayout.BeginArea(new Rect(10, 10, 500, 400));

            GUILayout.Box("Quest Debugger");

            GUILayout.Label("=== BUTTON CONTROLS ===", new GUIStyle(GUI.skin.label) { fontStyle = FontStyle.Bold });
            GUILayout.Label("A Button (Right) → Direction 1 (Front)");
            GUILayout.Label("B Button (Right) → Direction 2 (Back)");
            GUILayout.Label("X Button (Left) → Direction 3 (Left)");
            GUILayout.Label("Y Button (Left) → Direction 4 (Right)");

            GUILayout.Space(10);

            GUILayout.Label("=== MICROPHONE CONTROLS ===", new GUIStyle(GUI.skin.label) { fontStyle = FontStyle.Bold });
            GUILayout.Label("Grip Button → Toggle Microphone Recording");
            
            string micStatus = isRecording ? $"RECORDING... ({recordingTimer:F1}s)" : "Not Recording";
            GUILayout.Label($"Status: {micStatus}");

            GUILayout.Space(10);

            GUILayout.Label("=== DEBUG LOG ===", new GUIStyle(GUI.skin.label) { fontStyle = FontStyle.Bold });
            
            debugLog = GUILayout.TextArea(debugLog, GUILayout.Height(150));

            GUILayout.Space(10);

            if (GUILayout.Button("Clear Log", GUILayout.Height(30)))
            {
                debugLog = "";
            }

            GUILayout.EndArea();
        }

        public void TestSendCaption(string text)
        {
            if (singularityManager != null)
            {
                lastCapturedText = text;
                singularityManager.ProcessMessage(text);
                LogDebug($"[TEST] Caption sent: {text}");
            }
        }
    }
}
