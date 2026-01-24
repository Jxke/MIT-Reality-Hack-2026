using System;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;
using System.Collections.Concurrent;

public class QuestTcpClient : MonoBehaviour
{
    [Header("Arduino TCP Server")]
    public string arduinoIP = "10.29.193.69";
    public int port = 7000;

    TcpClient client;
    NetworkStream stream;
    Thread receiveThread;

    ConcurrentQueue<string> messageQueue = new ConcurrentQueue<string>();

    public static Action<string> OnMessageReceived;

    void Start()
    {
        receiveThread = new Thread(ConnectAndListen);
        receiveThread.IsBackground = true;
        receiveThread.Start();
    }

    void ConnectAndListen()
    {
        try
        {
            client = new TcpClient();
            client.Connect(arduinoIP, port);
            stream = client.GetStream();

            Debug.Log("TCP connected to Arduino");

            byte[] buffer = new byte[1024];
            StringBuilder sb = new StringBuilder();

            while (client.Connected)
            {
                int bytesRead = stream.Read(buffer, 0, buffer.Length);
                if (bytesRead <= 0)
                    continue;

                sb.Append(Encoding.UTF8.GetString(buffer, 0, bytesRead));

                // Process full messages framed by S ... E
                while (true)
                {
                    string data = sb.ToString();
                    int start = data.IndexOf('S');
                    int end = data.IndexOf('E');

                    if (start != -1 && end > start)
                    {
                        string message = data.Substring(start + 1, end - start - 1);
                        messageQueue.Enqueue(message);
                        sb.Remove(0, end + 1);
                    }
                    else
                    {
                        break;
                    }
                }
            }
        }
        catch (Exception e)
        {
            Debug.LogError("TCP error: " + e.Message);
        }
    }

    void Update()
    {
        while (messageQueue.TryDequeue(out string msg))
        {
            OnMessageReceived?.Invoke(msg);
        }
    }

    void OnApplicationQuit()
    {
        try
        {
            receiveThread?.Abort();
            stream?.Close();
            client?.Close();
        }
        catch { }
    }
}
