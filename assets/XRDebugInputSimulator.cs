using UnityEngine;
using System.Collections;
using Sngty;

public class XRDebugInputSimulator : MonoBehaviour
{
    [Header("References")]
    public SingularityManager singularityManager;
    public CaptionManager captionManager;
    public TCPGradientUIController gradientUI;

    [Header("Microphone Settings")]
    public float recordDuration = 5f;

    private AudioClip micClip;
    private bool recording;

    void Start()
    {
        if (captionManager == null)
            captionManager = FindObjectOfType<CaptionManager>();

        if (gradientUI == null)
            gradientUI = FindObjectOfType<TCPGradientUIController>();

        if (singularityManager == null)
            singularityManager = FindObjectOfType<SingularityManager>();

        Debug.Log("XR Debug Simulator Ready");
    }

    void Update()
    {
        HandleDirectionInputs();
        HandleMicInput();
    }

    void HandleDirectionInputs()
    {
        // LEFT (A button)
        if (OVRInput.GetDown(OVRInput.Button.One))
        {
            SimulateDirection(3); // Left
        }

        // RIGHT (B button)
        if (OVRInput.GetDown(OVRInput.Button.Two))
        {
            SimulateDirection(4); // Right
        }

        // BACK (X button)
        if (OVRInput.GetDown(OVRInput.Button.Three))
        {
            SimulateDirection(2); // Back
        }

        // FRONT (Y button)
        if (OVRInput.GetDown(OVRInput.Button.Four))
        {
            SimulateDirection(1); // Front
        }
    }

    void HandleMicInput()
    {
        if (OVRInput.GetDown(OVRInput.Button.PrimaryIndexTrigger) && !recording)
        {
            StartCoroutine(StartMicCapture());
        }
    }

    void SimulateDirection(int dir)
    {
        Debug.Log($"[DEBUG INPUT] Direction Triggered: {dir}");

        captionManager.SetDirection(dir);
        gradientUI.HandleDirection(dir);
    }

    IEnumerator StartMicCapture()
    {
        recording = true;

        Debug.Log("[DEBUG INPUT] Microphone capture started");

        micClip = Microphone.Start(null, false, (int)recordDuration, 44100);

        yield return new WaitForSeconds(recordDuration);

        Microphone.End(null);

        Debug.Log("[DEBUG INPUT] Microphone capture finished");

        // Placeholder transcription
        string fakeTranscript = "Debug microphone input detected";

        captionManager.ShowCaption(fakeTranscript);

        recording = false;
    }
}
