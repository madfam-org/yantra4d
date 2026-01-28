# Web Interface Documentation

**Tablaco Studio** is a local web application for visualizing, customizing, and verifying the design.

## Architecture

The app follows a standard client-server model:
-   **Frontend**: React (Vite)
-   **Backend**: Python (Flask)

### Backend (`web_interface/backend/`)

#### `app.py`
The Flask entry point. It exposes a REST API via port `5000`.

-   **API Endpoints**:
    -   `POST /api/render`:
        -   **Input**: JSON `{size, thick, show_base, ...}`
        -   **Action**: Calls OpenSCAD via subprocess with `-D` flags.
        -   **Output**: JSON `{stl_url: "..."}`
    -   `POST /api/verify`:
        -   **Action**: Runs `verify_design.py` against the last generated STL.
        -   **Output**: JSON `{passed: bool, output: str}`
-   **Static Serving**: Serves the generated `preview.stl` from the `static/` folder.

### Frontend (`web_interface/frontend/`)

Built with React + Vite + Three.js (Fiber).

#### Key Components
-   **`App.jsx`**: Main state container. Manages parameters and API calls.
-   **`Controls.jsx`**: Sidebar with sliders and checkboxes. Debounces input to avoid flooding the backend.
-   **`Viewer.jsx`**: The 3D view.
    -   Uses `@react-three/fiber` `Canvas`.
    -   Uses `STLLoader` to parse the binary STL.
    -   Includes `OrbitControls` for user interaction.

### Running the App

1.  **Start Backend**:
    ```bash
    python3 web_interface/backend/app.py
    ```
2.  **Start Frontend**:
    ```bash
    cd web_interface/frontend
    npm run dev
    ```
3.  **Access**: http://localhost:5173

[Back to Index](./index.md)
