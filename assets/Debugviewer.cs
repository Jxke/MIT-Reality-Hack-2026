using UnityEngine;
using TMPro;
using Sngty;

public class DebugViewer : MonoBehaviour
{
    public GameObject panel;
    public TMP_Text debugText;

    public SingularityManager singularity;

    private bool visible;

    private int packetCount;
    private int lastDirection;
    private string lastCaption = "None";

    void Start()
    {
        if (panel != null)
            panel.SetActive(false);

        if (singularity == null)
            singularity = FindObjectOfType<SingularityManager>();
    }

    void Update()
    {
        TogglePanel();
        UpdateDebugText();
    }

    void TogglePanel()
    {
        if (OVRInput.GetDown(OVRInput.Button.SecondaryThumbstick))
        {
            visible = !visible;

            if (panel != null)
                panel.SetActive(visible);
        }
    }

    void UpdateDebugText()
    {
        if (!visible || debugText == null || singularity == null)
            return;

        float fps = 1f / Time.deltaTime;

        string connectionStatus = singularity.IsConnected() ? "Connected" : "Disconnected";

        string ip = string.IsNullOrEmpty(singularity.clientIP) ? "Not Set" : singularity.clientIP;
        string port = singularity.clientPort.ToString();

        debugText.text =
            "=== SINGULARITY DEBUG ===\n\n" +

            "Connection\n" +
            $"IP: {ip}\n" +
            $"Port: {port}\n" +
            $"Status: {connectionStatus}\n\n" +

            "Network\n" +
            $"Packets Received: {packetCount}\n" +
            $"Last Direction: {lastDirection}\n\n" +

            "Captions\n" +
            $"Last Caption: {lastCaption}\n\n" +

            "System\n" +
            $"FPS: {fps:F1}";
    }

    public void LogPacket()
    {
        packetCount++;
    }

    public void LogDirection(int dir)
    {
        lastDirection = dir;
    }

    public void LogCaption(string caption)
    {
        lastCaption = caption;
    }

    // NEW: force refresh after UI input
    public void ForceRefresh()
    {
        UpdateDebugText();
    }
}