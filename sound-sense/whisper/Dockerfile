FROM debian:bookworm-slim AS builder
RUN apt-get update && apt-get install -y \
    build-essential cmake git libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN git clone --depth 1 https://github.com/ggml-org/whisper.cpp .
RUN cmake -B build \
    -DWHISPER_OPENBLAS=ON \
    -DWHISPER_BUILD_SERVER=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=OFF \
    && cmake --build build --config Release -j$(nproc)

FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y libopenblas0 libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/build/bin/whisper-server ./build/bin/whisper-server
EXPOSE 8080
