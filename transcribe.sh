#!/bin/bash

# Script to transcribe an audio file using whisper-cli

# Check if an audio file path is provided
if [ -z "$1" ]; then
  echo "Usage: ./transcribe.sh <audio_file_path>"
  exit 1
fi

AUDIO_FILE="$1"
WHISPER_CLI="../whisper.cpp/build/bin/whisper-cli"
MODEL_PATH="../whisper.cpp/models/ggml-base.en.bin"

# Check if the whisper-cli executable exists
if [ ! -f "$WHISPER_CLI" ]; then
  echo "Error: whisper-cli not found at $WHISPER_CLI. Please build the project first."
  exit 1
fi

# Check if the model file exists
if [ ! -f "$MODEL_PATH" ]; then
  echo "Error: model not found at $MODEL_PATH. Please download the model first (e.g., ./models/download-ggml-model.sh base.en)."
  exit 1
fi

# Check if the audio file exists
if [ ! -f "$AUDIO_FILE" ]; then
  echo "Error: audio file not found at $AUDIO_FILE."
  exit 1
fi

# Run the transcription
#echo "Transcribing $AUDIO_FILE..."
"$WHISPER_CLI" -m "$MODEL_PATH" -f "$AUDIO_FILE"
