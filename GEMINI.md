# ZapMeow

ZapMeow is a Go-based API that allows developers to interact with WhatsApp using the `whatsmeow` library. It supports multiple WhatsApp instances, sending various message types, and provides endpoints for managing instances and retrieving information.

## Key Technologies

- **Programming Language:** Go
- **Web Framework:** Gin
- **Database:** SQLite (with GORM)
- **Queueing:** Redis
- **WhatsApp Integration:** whatsmeow
- **API Documentation:** Swagger

## How to Run

1.  **Prerequisites:**
    *   Go (version 1.23 or later)
    *   Docker (optional, for running with Docker)

2.  **Configuration:**
    *   Copy `.env.example` to `.env` and update the environment variables.
    *   The `STORAGE_PATH` variable in `.env` is crucial as it defines where received media files will be saved. Ensure this directory exists and has the correct write permissions.
    *   The `DATABASE_PATH` variable in `.env` defines the path to the SQLite database file.

3.  **Running the Application:**
    *   **Locally:**
        ```bash
        go mod tidy
        go run cmd/server/main.go
        ```
    *   **With Docker:**
        ```bash
        docker build -t zapmeow .
        docker run -p 8900:8900 --env-file .env zapmeow
        ```

4.  **API Documentation:**
    *   Once the server is running, Swagger documentation is available at `http://localhost:8900/api/swagger/index.html`.

## Key Packages

-   **`cmd/server/main.go`**: The entry point of the application. It initializes the server, database, services, and routes.
-   **`api/`**: Contains the core application logic, separated into handlers, services, repositories, and models.
    -   **`handler/`**: Handles incoming HTTP requests.
    -   **`service/`**: Contains the business logic.
    -   **`repository/`**: Manages data persistence.
    -   **`model/`**: Defines the data structures.
-   **`pkg/`**: Contains reusable packages.
    -   **`whatsapp/`**: A wrapper around the `whatsmeow` library to handle WhatsApp communication.
    -   **`database/`**: Manages the database connection and migrations.
    -   **`queue/`**: Manages the Redis queue for background tasks.
-   **`config/`**: Handles application configuration loading from environment variables and YAML files.
-   **`worker/`**: Contains background workers, such as the `history_sync_worker.go` for synchronizing message history.

## Audio Transcription

The project includes a script `transcribe.sh` to transcribe audio files using `whisper.cpp`. Refer to the `README.md` for usage instructions.

## Deployment

To deploy the application, you need to build the binary and restart the service.

**Build the application:**

```bash
go build cmd/server/main.go
```

**Restart the service:**

```bash
sudo systemctl restart zapmeow
```
