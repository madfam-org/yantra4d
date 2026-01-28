# Web Interface Documentation

**Tablaco Studio** is a local web application for visualizing, customizing, and verifying the design.

---

## Key Features
- **Two-Step Workflow**:
    1.  **Unit Mode**: Visualize and verify a single `half_cube` unit. Adjust Size, Thickness, Rod Diameter, and Primitive Visibility.
    2.  **Grid Mode**: Generate a full `tablaco` grid using the defined unit. Adjust Rows, Columns, and Rod Extension.
- **Interactive 3D Viewer**: Real-time rendering of the generated STL (Unit or Grid) with loading progress.
- **One-Click Verification**: Run the `verify_design.py` suite directly from the UI (Unit Mode).
- **Live Parameter Controls**: Sliders and toggles update the model dynamically.
- **Theme Toggle**: Switch between Light, Dark, and System (Auto) modes. Preference is persisted.
- **Bilingual UI**: English and Spanish (Spanish is default). Toggled via a Globe icon.
- **Export Capabilities**:
    - **Download STL**: Save the current model as an STL file.
    - **Export Images**: Capture screenshots from predefined camera angles (Isometric, Top, Front, Right).

---

## Architecture

The app follows a standard client-server model:
-   **Frontend**: React (Vite) with Tailwind CSS and Shadcn UI.
-   **Backend**: Python (Flask) with Blueprint pattern.

### Backend Structure (`web_interface/backend/`)

```
backend/
├── app.py              # App factory, blueprint registration
├── config.py           # Centralized configuration (env vars)
├── requirements.txt    # Python dependencies
├── routes/
│   ├── render.py       # /api/estimate, /api/render, /api/render-stream
│   ├── health.py       # /api/health
│   └── verify.py       # /api/verify
├── services/
│   └── openscad.py     # OpenSCAD subprocess wrapper
└── static/             # Generated STL files
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/estimate` | POST | Estimate render time |
| `/api/render` | POST | Synchronous render |
| `/api/render-stream` | POST | SSE progress streaming |
| `/api/verify` | POST | Run verification suite |
| `/api/health` | GET | Health check for monitoring |

### Frontend (`web_interface/frontend/`)

Built with **React + Vite + Three.js (Fiber) + Tailwind CSS + Shadcn UI**.

#### Key Components
-   **`App.jsx`**: Main state container. Manages parameters, **mode state** (Unit vs Grid), theme/language toggles, and API calls.
-   **`Controls.jsx`**: Sidebar component. Renders different inputs based on the active mode (`mode` prop). Uses Shadcn `Slider`, `Checkbox`, and `Label`.
-   **`Viewer.jsx`**: The 3D view.
    -   Uses `@react-three/fiber` `Canvas` with `preserveDrawingBuffer` for screenshots.
    -   Uses `STLLoader` to parse the binary STL.
    -   Includes `OrbitControls` for user interaction.
    -   Exposes `ref` API with `captureSnapshot()` and `setCameraView(view)` methods.
    -   Displays a loading overlay with progress percentage.

#### Contexts (`web_interface/frontend/src/contexts/`)
-   **`ThemeProvider.jsx`**: Manages Light/Dark/System modes. Persists to `localStorage`. Applies `.dark` class to `<html>`.
-   **`LanguageProvider.jsx`**: Manages English/Spanish translations. Provides `t(key)` function for lookups.

---

## Running the App

### Development Mode
```bash
# Terminal 1: Backend
python3 web_interface/backend/app.py

# Terminal 2: Frontend
cd web_interface/frontend
npm run dev
```
Access: http://localhost:5173

### Production Mode
```bash
# Backend with gunicorn
cd web_interface/backend
gunicorn -w 2 -b 0.0.0.0:5000 --timeout 300 app:app

# Frontend (build + serve)
cd web_interface/frontend
npm run build
npm run preview
```

### Docker
```bash
docker-compose up --build
```
Access: http://localhost:3000 (frontend) / http://localhost:5000 (backend)

[Back to Index](./index.md)


