using UnityEngine;
using UnityEngine.UI;
using TMPro;

namespace Sngty
{
    public class DetailedDebugCheck : MonoBehaviour
    {
        void Start()
        {
            Debug.Log("\n========== DETAILED DEBUG CHECK ==========\n");

            // 1. Check SingularityManager
            SingularityManager sm = FindObjectOfType<SingularityManager>();
            Debug.Log($"1. SingularityManager: {(sm != null ? "✓ FOUND" : "✗ NULL")}");
            if (sm != null)
            {
                Debug.Log($"   - Caption Manager: {(sm.captionManager != null ? "✓" : "✗")}");
                Debug.Log($"   - Gradient Controller: {(sm.tCPGradientUIController != null ? "✓" : "✗")}");
            }

            // 2. Check CaptionManager
            CaptionManager cm = FindObjectOfType<CaptionManager>();
            Debug.Log($"\n2. CaptionManager: {(cm != null ? "✓ FOUND" : "✗ NULL")}");
            if (cm != null)
            {
                Debug.Log($"   - Prefab: {(cm.captionPrefab != null ? "✓ " + cm.captionPrefab.name : "✗ NULL")}");
                Debug.Log($"   - Spawn Root: {(cm.captionSpawnRoot != null ? "✓ " + cm.captionSpawnRoot.name : "✗ NULL")}");
                
                if (cm.captionPrefab != null)
                {
                    TMP_Text textComponent = cm.captionPrefab.GetComponentInChildren<TMPro.TMP_Text>();
                    Debug.Log($"   - Prefab has TMP_Text: {(textComponent != null ? "✓" : "✗")}");
                }
            }

            // 3. Check TCPGradientUIController
            TCPGradientUIController gc = FindObjectOfType<TCPGradientUIController>();
            Debug.Log($"\n3. TCPGradientUIController: {(gc != null ? "✓ FOUND" : "✗ NULL")}");
            if (gc != null)
            {
                Debug.Log($"   - Left Gradient: {(gc.leftGradient != null ? "✓ " + gc.leftGradient.gameObject.name : "✗ NULL")}");
                if (gc.leftGradient != null)
                {
                    Debug.Log($"     - Left enabled: {gc.leftGradient.gameObject.activeSelf}");
                    Debug.Log($"     - Left alpha: {gc.leftGradient.color.a}");
                }
                
                Debug.Log($"   - Right Gradient: {(gc.rightGradient != null ? "✓ " + gc.rightGradient.gameObject.name : "✗ NULL")}");
                if (gc.rightGradient != null)
                {
                    Debug.Log($"     - Right enabled: {gc.rightGradient.gameObject.activeSelf}");
                    Debug.Log($"     - Right alpha: {gc.rightGradient.color.a}");
                }
            }

            // 4. Check Canvases
            Canvas[] canvases = FindObjectsOfType<Canvas>();
            Debug.Log($"\n4. Canvases Found: {canvases.Length}");
            foreach (Canvas c in canvases)
            {
                Debug.Log($"   - {c.gameObject.name}");
                Debug.Log($"     - Render Mode: {c.renderMode}");
                Debug.Log($"     - Active: {c.gameObject.activeSelf}");
                Debug.Log($"     - Sorting Order: {c.sortingOrder}");
                
                if (c.renderMode == RenderMode.ScreenSpaceOverlay)
                {
                    Debug.Log($"     - Type: Screenspace Overlay (HUD)");
                }
                else if (c.renderMode == RenderMode.WorldSpace)
                {
                    Debug.Log($"     - Type: Worldspace");
                }
            }

            // 5. Check Main Camera
            Camera cam = Camera.main;
            Debug.Log($"\n5. Main Camera: {(cam != null ? "✓ FOUND" : "✗ NULL")}");
            if (cam != null)
            {
                Debug.Log($"   - Position: {cam.transform.position}");
                Debug.Log($"   - Near: {cam.nearClipPlane}, Far: {cam.farClipPlane}");
            }

            // 6. Test Direction Processing
            Debug.Log($"\n6. Testing Direction Processing...");
            if (sm != null)
            {
                Debug.Log("   - Calling ProcessMessage('1')...");
                sm.ProcessMessage("1");
                Debug.Log("   - Done");
            }

            // 7. Test Caption
            Debug.Log($"\n7. Testing Caption...");
            if (cm != null && cm.captionPrefab != null && cm.captionSpawnRoot != null)
            {
                Debug.Log("   - All caption requirements met, calling ShowCaption...");
                cm.ShowCaption("[TEST CAPTION]");
                Debug.Log("   - Done (check scene for caption)");
            }
            else
            {
                Debug.LogError("   - Cannot test caption: missing captionPrefab or captionSpawnRoot");
            }

            Debug.Log("\n========== END DEBUG CHECK ==========\n");
        }
    }
}
