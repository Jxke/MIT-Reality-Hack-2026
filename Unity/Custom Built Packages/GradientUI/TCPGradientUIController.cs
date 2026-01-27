using UnityEngine;
using UnityEngine.UI;

namespace Sngty
{
    public class TCPGradientUIController : MonoBehaviour
    {
        [Header("TCP Source")]
        public SingularityManager receiver;
        public bool autoFindReceiver = true;

        [Header("UI")]
        public Image leftGradient;
        public Image rightGradient;

        [Header("Fade Settings")]
        public float fadeDuration = 1f;
        public float holdDuration = 1f;

        [Header("Debug")]
        public bool logMessages;

        private float leftTargetAlpha;
        private float rightTargetAlpha;
        private float lastTriggerTime = -999f;
        private SingularityManager subscribedReceiver;

        void Start()
        {
            leftTargetAlpha = 0f;
            rightTargetAlpha = 0f;

            if (leftGradient != null)
            {
                SetImageAlpha(leftGradient, 0f);
            }

            if (rightGradient != null)
            {
                SetImageAlpha(rightGradient, 0f);
            }
        }

        void OnEnable()
        {
            TrySubscribe();
        }

        void OnDisable()
        {
            Unsubscribe();
        }

        void Update()
        {
            if (leftGradient != null)
            {
                SetImageAlpha(leftGradient, MoveAlpha(leftGradient.color.a, leftTargetAlpha));
            }

            if (rightGradient != null)
            {
                SetImageAlpha(rightGradient, MoveAlpha(rightGradient.color.a, rightTargetAlpha));
            }

            if (Time.time - lastTriggerTime > holdDuration)
            {
                leftTargetAlpha = 0f;
                rightTargetAlpha = 0f;
            }
        }

        public void HandleMessageFromEvent(string message)
        {
            HandleMessage(message);
        }

        private void HandleMessage(string message)
        {
            if (logMessages)
            {
                Debug.Log($"TCPGradientUIController received: {message}");
            }

            int value;
            if (!TryGetFirstInt(message, out value))
            {
                return;
            }

            lastTriggerTime = Time.time;

            switch (value)
            {
                case 1:
                    leftTargetAlpha = 1f;
                    rightTargetAlpha = 1f;
                    break;
                case 2:
                    leftTargetAlpha = 1f;
                    rightTargetAlpha = 0f;
                    break;
                case 3:
                    leftTargetAlpha = 0f;
                    rightTargetAlpha = 0f;
                    break;
                case 4:
                    leftTargetAlpha = 0f;
                    rightTargetAlpha = 1f;
                    break;
            }
        }

        private void TrySubscribe()
        {
            if (receiver == null && autoFindReceiver)
            {
                receiver = FindObjectOfType<SingularityManager>();
            }

            if (receiver == null)
            {
                return;
            }

            if (subscribedReceiver == receiver)
            {
                return;
            }

            Unsubscribe();
            receiver.onMessageRecieved.AddListener(HandleMessage);
            subscribedReceiver = receiver;
        }

        private void Unsubscribe()
        {
            if (subscribedReceiver != null)
            {
                subscribedReceiver.onMessageRecieved.RemoveListener(HandleMessage);
                subscribedReceiver = null;
            }
        }

        private float MoveAlpha(float current, float target)
        {
            if (fadeDuration <= 0f)
            {
                return target;
            }

            float step = Time.deltaTime / fadeDuration;
            return Mathf.MoveTowards(current, target, step);
        }

        private void SetImageAlpha(Image image, float alpha)
        {
            Color c = image.color;
            c.a = alpha;
            image.color = c;
        }

        private bool TryGetFirstInt(string message, out int value)
        {
            value = 0;
            if (string.IsNullOrEmpty(message))
            {
                return false;
            }

            for (int i = 0; i < message.Length; i++)
            {
                if (char.IsDigit(message[i]))
                {
                    value = message[i] - '0';
                    return true;
                }
            }

            return false;
        }
    }
}
