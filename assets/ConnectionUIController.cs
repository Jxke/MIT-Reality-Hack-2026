using TMPro;
using UnityEngine;
using Sngty;

public class ConnectionUIController : MonoBehaviour
{
    public TMP_InputField ipField;
    public TMP_InputField portField;

    public SingularityManager singularityManager;
    public DebugViewer debugViewer;

    public GameObject connectionPanel;

    public void ConnectPressed()
    {
        string ip = ipField.text.Trim();

        if (string.IsNullOrEmpty(ip))
        {
            Debug.LogError("IP field is empty");
            return;
        }

        if (!int.TryParse(portField.text.Trim(), out int port))
        {
            Debug.LogError("Invalid port value");
            return;
        }

        // APPLY VALUES
        singularityManager.clientIP = ip;
        singularityManager.clientPort = port;

        Debug.Log($"Values set: {ip}:{port}");

        // Refresh debug panel instantly
        if (debugViewer != null)
            debugViewer.ForceRefresh();

        // Start connection attempt
        singularityManager.ConnectWifiManual();

        // Hide panel AFTER values applied
        connectionPanel.SetActive(false);
    }
}