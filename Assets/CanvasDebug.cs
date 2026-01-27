using UnityEngine;

public class CanvasDebug : MonoBehaviour
{
    void Start()
    {
        Canvas canvas = GetComponent<Canvas>();
        if (canvas != null)
        {
            Debug.Log($"Canvas enabled: {canvas.enabled}");
            Debug.Log($"Canvas render mode: {canvas.renderMode}");
            Debug.Log($"Canvas sorting order: {canvas.sortingOrder}");
        }

        gameObject.SetActive(true);
        if (GetComponentInParent<Canvas>() != null)
        {
            Debug.Log("Canvas is active and in hierarchy");
        }
    }

    void Update()
    {
        // Ensure canvas and gradient images stay visible
        Canvas canvas = GetComponent<Canvas>();
        if (canvas != null && !canvas.enabled)
        {
            canvas.enabled = true;
        }
    }
}
