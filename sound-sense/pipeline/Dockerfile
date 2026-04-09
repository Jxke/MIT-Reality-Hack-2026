FROM python:3.12-slim

# Build tools + PulseAudio dev headers (needed to compile PortAudio with PA support)
RUN apt-get update && apt-get install -y \
    libsndfile1 libpulse0 libpulse-dev libasound2-dev \
    gcc python3-dev make curl autoconf libtool pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Build PortAudio from source with PulseAudio enabled.
# The distro's libportaudio2 package omits PulseAudio, so we compile our own.
RUN apt-get update && apt-get install -y git cmake g++ && rm -rf /var/lib/apt/lists/* && \
    git clone --depth 1 https://github.com/PortAudio/portaudio.git /tmp/portaudio && \
    cmake -S /tmp/portaudio -B /tmp/portaudio/build \
        -DPA_USE_ALSA=ON -DPA_USE_PULSEAUDIO=ON \
        -DBUILD_SHARED_LIBS=ON -DCMAKE_BUILD_TYPE=Release && \
    cmake --build /tmp/portaudio/build -j$(nproc) && \
    cmake --install /tmp/portaudio/build && ldconfig && \
    (nm /usr/local/lib/libportaudio.so.2 | grep -q PulseAudio && echo "PulseAudio: YES" || echo "PulseAudio: NO") && \
    rm -rf /tmp/portaudio

WORKDIR /app
COPY requirements.txt .

# Install Python deps, then remove the bundled PortAudio binary that ships
# with the sounddevice wheel so it uses our PulseAudio-enabled build instead.
RUN pip install --no-cache-dir -r requirements.txt && \
    find /usr/local/lib -path "*/sounddevice_data/portaudio-binaries/libportaudio*" -delete

COPY . .
CMD ["python", "-u", "main.py"]
