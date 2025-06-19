## ZapMeow

ZapMeow is a versatile API that allows developers to interact with WhatsApp using the [whatsmeow](https://github.com/tulir/whatsmeow) library. This API was designed to facilitate communication and allow the use of multiple instances of WhatsApp.

### Features

-   **Multi-Instance Support**: Seamlessly manage and interact with multiple WhatsApp instances concurrently.
-   **Message Sending**: Send text, image, and audio messages to WhatsApp contacts and groups.
-   **Phone Number Verification**: Check if phone numbers are registered on WhatsApp.
-   **Contact Information**: Obtain contact information.
-   **Profile Information**: Obtain profile information.
-   **QR Code Generation**: Generate QR codes to initiate WhatsApp login.
-   **Instance Status**: Retrieve the connection status of a specific instance of WhatsApp.

### Project Structure

The project is organized into the following main directories:

-   `api/`: Contains the HTTP handlers, services, models, repositories, and helpers for the API.
-   `cmd/`: Entry point for the application.
-   `config/`: Handles application configuration loading.
-   `docs/`: Contains Swagger documentation files.
-   `pkg/`: Includes reusable packages for database, HTTP, logging, queue, and the whatsmeow library wrapper.
-   `worker/`: Contains background workers, such as the history sync worker.

### Key Components

-   **Handlers**: Located in `api/handler`, these handle incoming HTTP requests and interact with services.
-   **Services**: Located in `api/service`, these contain the core business logic and interact with repositories and the `pkg/whatsapp` wrapper.
-   **Repositories**: Located in `api/repository`, these handle data persistence (e.g., accounts, messages).
-   **Helpers**: Located in `api/helper`, these provide utility functions.
-   **WhatsApp Wrapper**: Located in `pkg/whatsapp`, this package wraps the `go.mau.fi/whatsmeow` library and handles WhatsApp communication.

### Incoming Message Handling

Incoming messages are processed by an event handler within the `whatsappService` (`api/service/whatsapp_service.go`). When a new message event is received:

1.  The message is parsed.
2.  If the message contains media (image, audio, document), the media data is saved to disk using the `helper.SaveMedia` function.
3.  The message details, including the path to the saved media file (if applicable), are stored in the database.
4.  A webhook request is sent to the configured `WebhookURL` with the message details.

### Configuration

Configuration is loaded from the `.env` file using the `config` package. Key configuration variables include:

-   `DATABASE_URL`: Database connection string.
-   `REDIS_URL`: Redis connection string for the queue.
-   `STORAGE_PATH`: **The directory where received media files will be saved.** Ensure this directory has appropriate write permissions.
-   `WEBHOOK_URL`: The URL where incoming message notifications will be sent.
-   `HISTORY_SYNC`: Enable or disable history synchronization.

### Getting Started

To get started with the ZapMeow API, follow these simple steps:

1. **Clone the Repository**: Clone this repository to your local machine using the following command:

    ```sh
    git clone git@github.com:capsulbrasil/zapmeow.git
    ```

2. **Configuration**: Set up your project configuration by copying the provided `.env.example` file and updating the environment variables.

    - Navigate to the project directory:

        ```sh
        cd zapmeow
        ```

    - Create a copy of the `.env.example` file as `.env`:

        ```sh
        cp .env.example .env
        ```

    - Open the `.env` file using your preferred text editor and update the necessary environment variables.

3. **Install Dependencies**: Install the project dependencies using the following command:

    ```sh
    go mod tidy
    ```

4. **Start the API**: Run the API server by executing the following command:

    ```sh
    ./zapmeow
    ```

5. **Access Swagger Documentation**: You can access the Swagger documentation by visiting the following URL in your web browser:

    ```
    http://localhost:8900/api/swagger/index.html
    ```

    The Swagger documentation provides detailed information about the available API endpoints, request parameters, and response formats.

Now, your ZapMeow API is up and running, ready for you to start interacting with WhatsApp instances programmatically.

### Audio Transcription

The project includes a script `transcribe.sh` to transcribe audio files using the `whisper.cpp` library.

**Prerequisites:**

1.  **Build `whisper.cpp`**: Ensure that you have successfully built the `whisper.cpp` project. The script expects the `whisper-cli` executable to be at `../whisper.cpp/build/bin/whisper-cli`.
2.  **Download Model**: Download a `whisper.cpp` compatible model and place it in the `../whisper.cpp/models/` directory. The script defaults to using `ggml-base.en.bin`, so you might need to run `./models/download-ggml-model.sh base.en` from within the `whisper.cpp` directory.

**Usage:**

To transcribe an audio file, run the script from the project root directory with the path to the audio file as an argument:

```sh
./transcribe.sh <path_to_your_audio_file>
```

For example:

```sh
./transcribe.sh A58724DD983F41155872C278E700C296.oga
```

The script will output the transcription to the console. Make sure the audio file exists and the paths to `whisper-cli` and the model are correct within the `transcribe.sh` script if you have a different setup.
