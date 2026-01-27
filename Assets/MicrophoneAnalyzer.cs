using UnityEngine;
using System.Collections;

namespace Sngty
{
    /// <summary>
    /// Simple microphone audio analyzer for testing caption system
    /// Analyzes audio input and sends test captions based on detected audio
    /// </summary>
    public class MicrophoneAnalyzer : MonoBehaviour
    {
        [Header("Audio Input")]
        public int sampleRate = 16000;
        public float recordingLength = 3f;
        
        [Header("Analysis")]
        public float loudnessThreshold = 0.02f;
        public bool frequencyBasedResponse = true;

        [Header("Caption Suggestions")]
        public string[] lowFrequencyHints = new string[] { "Deep voice detected", "Low frequency sound" };
        public string[] highFrequencyHints = new string[] { "High pitch detected", "Sharp sound" };
        public string[] normalFrequencyHints = new string[] { "Normal voice detected", "Speech detected" };

        private AudioClip microphoneClip;
        private float[] frequencyBands = new float[8];

        public float GetAudioLoudness(AudioClip clip)
        {
            if (clip == null) return 0f;

            float[] samples = new float[clip.samples * clip.channels];
            clip.GetData(samples, 0);

            float loudness = 0f;
            foreach (float sample in samples)
            {
                loudness += Mathf.Abs(sample);
            }

            return loudness / samples.Length;
        }

        public void AnalyzeFrequency(AudioClip clip)
        {
            if (clip == null) return;

            float[] samples = new float[clip.samples];
            clip.GetData(samples, 0);

            // Simple frequency analysis (FFT would be better but this is simpler)
            for (int i = 0; i < frequencyBands.Length; i++)
            {
                frequencyBands[i] = 0f;
            }

            // Divide into 8 bands and analyze
            int bandSize = samples.Length / frequencyBands.Length;
            for (int b = 0; b < frequencyBands.Length; b++)
            {
                float sum = 0f;
                for (int i = 0; i < bandSize; i++)
                {
                    int index = b * bandSize + i;
                    if (index < samples.Length)
                    {
                        sum += Mathf.Abs(samples[index]);
                    }
                }
                frequencyBands[b] = sum / bandSize;
            }
        }

        public string GetCaptionSuggestion(AudioClip clip)
        {
            float loudness = GetAudioLoudness(clip);

            if (loudness < loudnessThreshold)
            {
                return "Silence detected";
            }

            AnalyzeFrequency(clip);

            // Determine dominant frequency range
            float lowFreq = frequencyBands[0] + frequencyBands[1];
            float midFreq = frequencyBands[2] + frequencyBands[3] + frequencyBands[4];
            float highFreq = frequencyBands[5] + frequencyBands[6] + frequencyBands[7];

            if (highFreq > midFreq && highFreq > lowFreq)
            {
                return highFrequencyHints[Random.Range(0, highFrequencyHints.Length)];
            }
            else if (lowFreq > midFreq && lowFreq > highFreq)
            {
                return lowFrequencyHints[Random.Range(0, lowFrequencyHints.Length)];
            }
            else
            {
                return normalFrequencyHints[Random.Range(0, normalFrequencyHints.Length)];
            }
        }

        public float[] GetFrequencyBands()
        {
            return frequencyBands;
        }
    }
}
