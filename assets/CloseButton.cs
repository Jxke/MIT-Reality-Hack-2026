using UnityEngine;

public class CloseButton : MonoBehaviour
{
    // This class can be expanded with additional functionality 
    public CloseButton Button;

    public void OnClick()
    {
        Button.gameObject.SetActive(false);
    }

}
