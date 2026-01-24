using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;
using UnityEngine.Android;
using System.Net.Sockets;
using System.Threading.Tasks;
using System.Net;
using System;
using System.Diagnostics;
using Debug = UnityEngine.Debug;

namespace Sngty
{
    public class SingularityManager : MonoBehaviour
    {
        public UnityEvent onConnected;
        public UnityEvent<string> onMessageRecieved;
        public UnityEvent<string> onError;

        [Header("Caption System")]
        public CaptionManager captionManager;

        private AndroidJavaClass BluetoothManager;
        private AndroidJavaObject bluetoothManager;
        private List<AndroidJavaObject> connectedDevices;

        public TCPGradientUIController tCPGradientUIController;

        

        public enum ConnectionType
        {
            Bluetooth,
            Wifi
        }

        public ConnectionType connectionType = ConnectionType.Wifi;

        [Header("Wifi Settings")]
        public string clientIP;
        public int clientPort = 7000;

        private TcpClient tcpClient;
        private NetworkStream tcpStream;

        void Awake()
        {
            if (connectionType == ConnectionType.Bluetooth)
            {
                RequestBluetoothPermissions();

                BluetoothManager = new AndroidJavaClass("com.harrysoft.androidbluetoothserial.BluetoothManager");
                bluetoothManager = BluetoothManager.CallStatic<AndroidJavaObject>("getInstance");
                connectedDevices = new List<AndroidJavaObject>();
            }

            Debug.Log("Starting Singularity Manager...");
            ConnectWifi();
        }

        #region WIFI

        private async void ConnectWifi()
        {
            try
            {
                Debug.Log("Connecting to client: " + clientIP);
                tcpClient = new TcpClient();
                await tcpClient.ConnectAsync(clientIP, clientPort);

                if (tcpClient.Connected)
                {
                    tcpStream = tcpClient.GetStream();
                    onConnected.Invoke();
                    Debug.Log("Connected!");
                    ReadWifiMessage();
                }
            }
            catch (Exception e)
            {
                onError.Invoke("Failed to connect: " + e.Message);
            }
        }

        private async void ReadWifiMessage()
        {
            byte[] buffer = new byte[1024];
            string accumulatedData = "";

            while (tcpClient != null && tcpClient.Connected)
            {
                if (tcpStream.DataAvailable)
                {
                    int bytesRead = await tcpStream.ReadAsync(buffer, 0, buffer.Length);
                    accumulatedData += System.Text.Encoding.ASCII.GetString(buffer, 0, bytesRead);

                    while (true)
                    {
                        int start = accumulatedData.IndexOf("S", StringComparison.Ordinal);
                        int end = accumulatedData.IndexOf("E\n", start + 1, StringComparison.Ordinal);

                        if (start == -1 || end == -1)
                            break;

                        string msg = accumulatedData.Substring(start + 1, end - start - 1).Trim();
                        accumulatedData = accumulatedData.Substring(end + 2);

                        HandleIncomingMessage(msg);
                    }
                }
                await Task.Delay(30);
            }

            onError.Invoke("Connection lost");
        }

        private void HandleIncomingMessage(string msg)
        {
            if (string.IsNullOrEmpty(msg)) return;

            // Direction messages
            if (msg == "1" || msg == "2" || msg == "3" || msg == "4")
            {
                int dir = int.Parse(msg);
                
                captionManager?.SetDirection(dir);
                tCPGradientUIController?.HandleDirection(dir);
                Debug.Log($"Direction set to: {dir}");
                return;
            }

            // Caption text
            captionManager?.ShowCaption(msg);
            onMessageRecieved.Invoke(msg);
            Debug.Log($"Caption: {msg}");
        }

        #endregion

        #region BLUETOOTH

        public void ConnectToDevice(DeviceSignature sig)
        {
            if (connectionType == ConnectionType.Wifi)
            {
                ConnectWifi();
                return;
            }

            AndroidJavaClass Schedulers = new AndroidJavaClass("io.reactivex.schedulers.Schedulers");
            AndroidJavaClass AndroidSchedulers = new AndroidJavaClass("io.reactivex.android.schedulers.AndroidSchedulers");

            bluetoothManager.Call<AndroidJavaObject>("openSerialDevice", sig.mac)
                .Call<AndroidJavaObject>("subscribeOn", Schedulers.CallStatic<AndroidJavaObject>("io"))
                .Call<AndroidJavaObject>("observeOn", AndroidSchedulers.CallStatic<AndroidJavaObject>("mainThread"))
                .Call("subscribe", new RxSingleObserver(onError, onConnected, OnBluetoothMessage, connectedDevices));
        }

        private void OnBluetoothMessage(string msg)
        {
            HandleIncomingMessage(msg);
        }

        #endregion

        #region SEND / DISCONNECT

        public void sendMessage(string message)
        {
            if (connectionType == ConnectionType.Wifi && tcpClient != null && tcpClient.Connected)
            {
                try
                {
                    byte[] data = System.Text.Encoding.ASCII.GetBytes(message + "\n");
                    tcpStream.Write(data, 0, data.Length);
                }
                catch (Exception e)
                {
                    onError.Invoke("Send failed: " + e.Message);
                }
            }
        }

        public void DisconnectAll()
        {
            if (tcpClient != null)
            {
                tcpStream?.Close();
                tcpClient.Close();
                tcpClient = null;
            }

            bluetoothManager?.Call("close");
            connectedDevices?.Clear();
        }

        void OnApplicationQuit()
        {
            DisconnectAll();
        }

        #endregion

        #region PERMISSIONS

        void RequestBluetoothPermissions()
        {
            string[] permissions =
            {
                "android.permission.BLUETOOTH",
                "android.permission.BLUETOOTH_ADMIN",
                "android.permission.BLUETOOTH_CONNECT",
                "android.permission.BLUETOOTH_SCAN"
            };

            Permission.RequestUserPermissions(permissions);
        }

        #endregion

        #region RX OBSERVERS

        class RxSingleObserver : AndroidJavaProxy
        {
            private UnityEvent<string> onErrorEvent;
            private UnityEvent onConnectedEvent;
            private Action<string> onMessageCallback;
            private List<AndroidJavaObject> connectedDevices;

            public RxSingleObserver(
                UnityEvent<string> onErrorEvent,
                UnityEvent onConnectedEvent,
                Action<string> onMessageCallback,
                List<AndroidJavaObject> connectedDevices
            ) : base("io.reactivex.SingleObserver")
            {
                this.onErrorEvent = onErrorEvent;
                this.onConnectedEvent = onConnectedEvent;
                this.onMessageCallback = onMessageCallback;
                this.connectedDevices = connectedDevices;
            }

            void onError(AndroidJavaObject e)
            {
                onErrorEvent.Invoke(e.Call<string>("getMessage"));
            }

            void onSuccess(AndroidJavaObject connectedDevice)
            {
                onConnectedEvent.Invoke();

                AndroidJavaObject deviceInterface = connectedDevice.Call<AndroidJavaObject>("toSimpleDeviceInterface");
                deviceInterface.Call("setMessageReceivedListener", new MessageReceivedListener(onMessageCallback));
                connectedDevices.Add(connectedDevice);
            }
        }

        class MessageReceivedListener : AndroidJavaProxy
        {
            private Action<string> callback;

            public MessageReceivedListener(Action<string> callback)
                : base("com.harrysoft.androidbluetoothserial.SimpleBluetoothDeviceInterface$OnMessageReceivedListener")
            {
                this.callback = callback;
            }

            void onMessageReceived(string message)
            {
                callback?.Invoke(message);
            }
        }

        #endregion
    }

    public struct DeviceSignature
    {
        public string name;
        public string mac;
    }
}
