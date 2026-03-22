using TMPro;
using UnityEngine;
using System.Collections;

public class CaptionManager : MonoBehaviour
{
    [Header("Caption Setup")]
    public GameObject captionPrefab;
    public Transform captionSpawnRoot;

    [Header("Timing")]
    public float captionLifetime = 3f;

    private SoundDirection currentDirection = SoundDirection.Front;

    // Called by TCP when a direction number arrives
    public void SetDirection(int dir)
    {
        currentDirection = dir switch
        {
            1 => SoundDirection.Front,
            2 => SoundDirection.Back,
            3 => SoundDirection.Left,
            4 => SoundDirection.Right,
            _ => currentDirection
        };
    }

    // Called by TCP when text arrives
    public void ShowCaption(string text)
    {
        GameObject caption = Instantiate(captionPrefab, captionSpawnRoot);

        TMP_Text tmp = caption.GetComponentInChildren<TMP_Text>();
        tmp.text = text;

        PositionCaption(caption.transform, currentDirection);

        StartCoroutine(DestroyAfter(caption, captionLifetime));
    }

    void PositionCaption(Transform caption, SoundDirection dir)
    {
        Camera cam = Camera.main;

        Vector3 offset = dir switch
        {
            SoundDirection.Front => cam.transform.forward,
            SoundDirection.Back => -cam.transform.forward,
            SoundDirection.Left => -cam.transform.right,
            SoundDirection.Right => cam.transform.right,
            _ => cam.transform.forward
        };

        caption.position = cam.transform.position + offset * 2f + Vector3.up * 0.3f;
        caption.rotation = Quaternion.LookRotation(caption.position - cam.transform.position);
    }

    IEnumerator DestroyAfter(GameObject obj, float t)
    {
        yield return new WaitForSeconds(t);
        Destroy(obj);
    }
}

public enum SoundDirection
{
    Front,
    Back,
    Left,
    Right
}
