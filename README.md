raspberry-pi-gps-logger/
├── README.md                          # Main overview (objectives, features, quick start)
├── docs/
│   ├── DEPLOYMENT.md                  # Docker deployment guide
│   ├── ARCHITECTURE.md                # System architecture & design
│   └── CONFIGURATION.md               # Configuration options
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.lte
├── requirements.txt
├── .gitignore
├── .dockerignore
├── src/
│   ├── gps_logger.py
│   ├── geofence_validator.py
│   ├── lte_monitor.py
│   └── utils/
├── config/
│   ├── geofence.geojson.example
│   └── config.env.example
├── data/
│   └── .gitkeep
└── logs/
    └── .gitkeep
