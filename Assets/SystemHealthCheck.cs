using UnityEngine;

namespace Sngty
{
    public class SystemHealthCheck : MonoBehaviour
    {
        void Start()
        {
            Debug.Log("\n=== SYSTEM HEALTH CHECK ===\n");

            // Check SingularityManager
            SingularityManager singularityManager = FindObjectOfType<SingularityManager>();
            if (singularityManager != null)
            {
                Debug.Log("✓ SingularityManager found");
                if (singularityManager.captionManager != null)
                    Debug.Log("  ✓ CaptionManager assigned");
                else
                    Debug.LogError("  ✗ CaptionManager NOT assigned!");

                if (singularityManager.tCPGradientUIController != null)
                    Debug.Log("  ✓ TCPGradientUIController assigned");
                else
                    Debug.LogError("  ✗ TCPGradientUIController NOT assigned!");
            }
            else
                Debug.LogError("✗ SingularityManager NOT found!");

            // Check CaptionManager
            CaptionManager captionManager = FindObjectOfType<CaptionManager>();
            if (captionManager != null)
            {
                Debug.Log("✓ CaptionManager found");
                if (captionManager.captionPrefab != null)
                    Debug.Log("  ✓ captionPrefab assigned");
                else
                    Debug.LogError("  ✗ captionPrefab NOT assigned!");

                if (captionManager.captionSpawnRoot != null)
                    Debug.Log("  ✓ captionSpawnRoot assigned");
                else
                    Debug.LogError("  ✗ captionSpawnRoot NOT assigned!");
            }
            else
                Debug.LogError("✗ CaptionManager NOT found!");

            // Check TCPGradientUIController
            TCPGradientUIController gradientController = FindObjectOfType<TCPGradientUIController>();
            if (gradientController != null)
            {
                Debug.Log("✓ TCPGradientUIController found");
                if (gradientController.leftGradient != null)
                    Debug.Log("  ✓ leftGradient assigned");
                else
                    Debug.LogError("  ✗ leftGradient NOT assigned!");

                if (gradientController.rightGradient != null)
                    Debug.Log("  ✓ rightGradient assigned");
                else
                    Debug.LogError("  ✗ rightGradient NOT assigned!");
            }
            else
                Debug.LogError("✗ TCPGradientUIController NOT found!");

            // Check QuestDebugger
            QuestDebugger questDebugger = FindObjectOfType<QuestDebugger>();
            if (questDebugger != null)
            {
                Debug.Log("✓ QuestDebugger found");
                if (questDebugger.singularityManager != null)
                    Debug.Log("  ✓ singularityManager assigned");
                else
                    Debug.LogWarning("  ⚠ singularityManager NOT assigned (will auto-find)");
            }
            else
                Debug.LogWarning("⚠ QuestDebugger NOT found (optional)");

            // Check Canvases
            Canvas[] canvases = FindObjectsOfType<Canvas>();
            Debug.Log($"\n✓ Found {canvases.Length} Canvas(es)");
            foreach (Canvas canvas in canvases)
            {
                Debug.Log($"  - {canvas.gameObject.name}: {canvas.renderMode}, Sorting Order: {canvas.sortingOrder}");
            }

            // Check Main Camera
            Camera mainCamera = Camera.main;
            if (mainCamera != null)
            {
                Debug.Log($"\n✓ Main Camera found");
                Debug.Log($"  - Near Clip: {mainCamera.nearClipPlane}");
                Debug.Log($"  - Far Clip: {mainCamera.farClipPlane}");
            }
            else
                Debug.LogError("\n✗ Main Camera NOT found!");

            Debug.Log("\n=== END HEALTH CHECK ===\n");
        }
    }
}
