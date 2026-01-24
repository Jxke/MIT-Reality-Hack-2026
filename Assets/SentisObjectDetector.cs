using UnityEngine;
using Unity.Barracuda;
using System.Collections.Generic;

public class SentisObjectDetector : MonoBehaviour
{
    [Header("Model Settings")]
    public NNModel faceDetectionModel;
    public TextAsset labelsFile;

    [Header("Detection Settings")]
    public float confidenceThreshold = 0.5f;
    public int inferenceInterval = 4;
    public int inputSize = 320;

    [Header("Passthrough Camera")]
    public OVRPassthroughLayer passthroughLayer;

    private IWorker worker;
    private string[] labels;
    private int frameCount;
    private Model model;
    private Texture2D cameraTexture;

    void Start()
    {
        if (faceDetectionModel == null)
        {
            Debug.LogError("Face detection model not assigned!");
            return;
        }

        try
        {
            model = ModelLoader.Load(faceDetectionModel);
            worker = WorkerFactory.CreateWorker(WorkerFactory.Type.ComputePrecompiled, model);
            
            if (labelsFile != null)
            {
                labels = labelsFile.text.Split('\n', System.StringSplitOptions.RemoveEmptyEntries);
            }
            
            Debug.Log("SentisObjectDetector initialized successfully");
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Failed to initialize detector: {e.Message}");
        }
    }

    public List<Detection> DetectFaces(Texture source)
    {
        if (worker == null || source == null)
            return null;

        frameCount++;
        if (frameCount % inferenceInterval != 0)
            return null;

        try
        {
            // Preprocess input texture
            var input = PreprocessTexture(source, inputSize, inputSize);
            
            // Run inference
            worker.Execute(input);
            
            // Parse output
            return ParseDetectionOutput(worker);
        }
        catch (System.Exception e)
        {
            Debug.LogError($"Detection error: {e.Message}");
            return null;
        }
    }

    private Tensor PreprocessTexture(Texture source, int width, int height)
    {
        // Create a readable copy of the texture
        RenderTexture rt = RenderTexture.GetTemporary(source.width, source.height, 0);
        Graphics.Blit(source, rt);
        
        RenderTexture.active = rt;
        Texture2D readableTex = new Texture2D(source.width, source.height, TextureFormat.RGB24, false);
        readableTex.ReadPixels(new Rect(0, 0, source.width, source.height), 0, 0);
        readableTex.Apply();
        RenderTexture.active = null;
        RenderTexture.ReleaseTemporary(rt);

        // Create tensor from texture
        var tensor = new Tensor(readableTex, channels: 3);
        Destroy(readableTex);
        
        return tensor;
    }

    private List<Detection> ParseDetectionOutput(IWorker worker)
    {
        var detections = new List<Detection>();
        
        // Get output tensor from worker
        var output = worker.PeekOutput();
        
        if (output == null)
            return detections;

        // Parse detections based on YOLO output format
        // This is a simplified parser - adjust based on your specific model output
        float[] outputData = output.AsFloats();
        
        for (int i = 0; i < outputData.Length; i += 6)
        {
            if (i + 5 >= outputData.Length)
                break;

            float confidence = outputData[i + 4];
            
            if (confidence >= confidenceThreshold)
            {
                var detection = new Detection
                {
                    x = outputData[i],
                    y = outputData[i + 1],
                    width = outputData[i + 2],
                    height = outputData[i + 3],
                    confidence = confidence,
                    classId = (int)outputData[i + 5],
                    label = labels != null && (int)outputData[i + 5] < labels.Length 
                        ? labels[(int)outputData[i + 5]] 
                        : "Unknown"
                };
                
                detections.Add(detection);
            }
        }

        return detections;
    }

    void OnDestroy()
    {
        worker?.Dispose();
        model?.Dispose();
    }
}

public class Detection
{
    public float x;
    public float y;
    public float width;
    public float height;
    public float confidence;
    public int classId;
    public string label;
}
