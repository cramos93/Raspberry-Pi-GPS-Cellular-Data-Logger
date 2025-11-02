graph TB
    %% -------------------- HARDWARE --------------------
    subgraph HW["🔧 HARDWARE LAYER"]
        GPS[GPS Receiver<br/>BU-353N]
        LTE[LTE Modem<br/>EM7565<br/>Optional]
    end

    GPS -->|USB/NMEA| PI{{"🖥️ RASPBERRY PI 5<br/>Central Processing Unit"}}
    LTE -.->|USB/AT| PI

    %% -------------------- SOFTWARE --------------------
    subgraph SW["💾 SOFTWARE LAYER"]
        direction TB
        PARSE[GPS Parser &<br/>Movement Calculator]
        CORE["⚙️ CORE PROCESSING<br/>📍 Location Tracking · ⚡ Speed · 🧭 Heading · 📊 Parameters"]
        DB[(Time-Series Database<br/>SQLite / PostgreSQL)]
        META[LTE/GSM<br/>Metadata Collector<br/>Optional]
    end

    PI --> PARSE
    PI -.-> META
    PARSE --> CORE
    CORE -->|Primary Flow| DB
    META -.->|Cell Data| DB

    %% -------------------- OPTIONAL FEATURES --------------------
    subgraph OPT["📌 OPTIONAL FEATURES"]
        FENCE[Geofence Validator<br/>GeoJSON · Optional]
        NOTIFY[Push Notification<br/>ntfy.sh · Optional]
    end

    DB -.-> FENCE
    FENCE -.-> NOTIFY

    %% -------------------- DATA-VIZ EXPORTS (to the right) --------------------
    subgraph EXPORTS["📤 Data Visualization Artifacts"]
        direction TB
        CSV[Formatted CSV<br/>for Charts/Dashboards]
        GEO[GeoJSON Feature Collection<br/>for Maps]
    end

    DB -->|Export| CSV
    DB -->|Export| GEO

    %% -------------------- STYLES --------------------
    style HW fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    style SW fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style OPT fill:#fff3e0,stroke:#ef6c00,stroke-width:2px
    style EXPORTS fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px

    style PI fill:#4caf50,stroke:#1b5e20,stroke-width:4px
    style CORE fill:#ffd54f,stroke:#f57c00,stroke-width:3px
    style DB fill:#ffb74d,stroke:#e64a19,stroke-width:2px

    style GPS fill:#90caf9,stroke:#1565c0,stroke-width:2px
    style LTE fill:#b0bec5,stroke:#455a64,stroke-width:1px,stroke-dasharray:5 5
    style META fill:#ce93d8,stroke:#6a1b9a,stroke-width:1px,stroke-dasharray:5 5
    style FENCE fill:#bcaaa4,stroke:#5d4037,stroke-width:1px,stroke-dasharray:5 5
    style NOTIFY fill:#bcaaa4,stroke:#5d4037,stroke-width:1px,stroke-dasharray:5 5
