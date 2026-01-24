using UnityEngine;
//hello
public class LightBlink : MonoBehaviour
{
    [Header("Blink Objects")]
    public GameObject blinkObject1;
    public GameObject blinkObject2;

    [Header("Blink Settings")]
    public float blinkInterval = 1f;

    private float timeSinceLastBlink = 0f;
    private bool isFirstObjectActive = true;

    void Start()
    {
        // Initialize state
        if (blinkObject1 != null)
            blinkObject1.SetActive(true);
        if (blinkObject2 != null)
            blinkObject2.SetActive(false);
    }

    void Update()
    {
        timeSinceLastBlink += Time.deltaTime;

        if (timeSinceLastBlink >= blinkInterval)
        {
            timeSinceLastBlink = 0f;
            ToggleBlink();
        }
    }

    private void ToggleBlink()
    {
        isFirstObjectActive = !isFirstObjectActive;

        if (blinkObject1 != null)
            blinkObject1.SetActive(isFirstObjectActive);
        if (blinkObject2 != null)
            blinkObject2.SetActive(!isFirstObjectActive);
    }
}
