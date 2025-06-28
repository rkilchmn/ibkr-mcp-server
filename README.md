# IBKR MCP Server

This project is a FastAPI application that manages and interacts with the Interactive Brokers (IBKR) Gateway through Docker containers. The IBKR Gateway starts automatically when the server starts.

## Features

- **Automatic Docker Container Management**: IBKR Gateway Docker container starts automatically with the server
- **RESTful API**: Complete API for gateway monitoring and IBKR interactions
- **Health Monitoring**: Real-time status and health checks
- **Log Management**: Access to container logs and debugging information
- **Portfolio Management**: Retrieve account information and portfolio positions

## Project Structure

```
ibkr-mcp-server
├── app
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── api
│   │   ├── __init__.py
│   │   └── endpoints
│   │       ├── __init__.py
│   │       ├── portfolio.py    # Portfolio endpoints
│   │       └── gateway.py      # Gateway monitoring endpoints
│   ├── core
│   │   ├── __init__.py
│   │   └── config.py
│   ├── models
│   │   ├── __init__.py
│   │   └── portfolio.py
│   ├── services
│   │   ├── __init__.py
│   │   └── ibkr_service.py
│   └── gateway
│       ├── __init__.py
│       ├── docker_service.py   # Docker container management
│       └── gateway_manager.py  # High-level gateway interface
├── main.py                     # Simple entry point
├── pyproject.toml
└── README.md
```

## Prerequisites

- Python 3.13+
- Docker installed and running
- IBKR TWS or Gateway running (for trading operations)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ibkr-mcp-server
   ```

2. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv sync

   # Or using pip
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file in the root directory with your IBKR credentials:
   ```bash
   cp env.example .env
   # Edit .env with your actual credentials
   ```

## Usage

### Starting the Server

```bash
# Start the FastAPI server (IBKR Gateway starts automatically)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API documentation will be available at `http://localhost:8000/docs`.

### API Endpoints

#### Gateway Monitoring

- `GET /gateway/status` - Get gateway status and health
- `GET /gateway/logs` - Get container logs

#### IBKR Interactions

- `POST /gateway/connect` - Connect to IBKR TWS/Gateway
- `POST /gateway/disconnect` - Disconnect from IBKR
- `GET /gateway/account` - Get account information
- `GET /gateway/portfolio` - Get portfolio positions

### Example API Usage

#### Get Gateway Status

```bash
curl "http://localhost:8000/gateway/status"
```

#### Connect to IBKR

```bash
curl -X POST "http://localhost:8000/gateway/connect" \
  -H "Content-Type: application/json" \
  -d '{
    "host": "127.0.0.1",
    "port": 4001,
    "client_id": 1
  }'
```

#### Get Portfolio

```bash
curl "http://localhost:8000/gateway/portfolio"
```

## Configuration

### Environment Variables

Create a `.env` file for your IBKR credentials:

```env
# IBKR Gateway credentials
IBKR_GATEWAY_USERNAME=your_ibkr_username
IBKR_GATEWAY_PASSWORD=your_ibkr_password
```

### Docker Container Settings

The IBKR Gateway container is automatically configured with:

- **Ports**: 6080, 8888, 7462 (for different services)
- **Image**: `ghcr.io/extrange/ibkr:stable`
- **Auto-restart**: Container restarts automatically unless stopped manually

## Docker Image

The application uses the `ghcr.io/extrange/ibkr:stable` Docker image, which provides:

- IBKR Gateway functionality
- REST API interface
- WebSocket support
- Configuration management

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Code Style

The project uses:
- **Indentation**: 2 spaces (Python)
- **Type hints**: Full type annotation support
- **Async/await**: Asynchronous programming patterns
- **Logging**: Structured logging throughout

### Adding New Features

1. **Docker Service**: Add new container management features in `app/gateway/docker_service.py`
2. **Gateway Manager**: Extend high-level functionality in `app/gateway/gateway_manager.py`
3. **API Endpoints**: Add new endpoints in `app/api/endpoints/gateway.py`

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker daemon is started
2. **Port conflicts**: Check if ports 6080, 8888, or 7462 are in use
3. **Permission issues**: Ensure your user has Docker permissions
4. **IBKR connection**: Verify TWS/Gateway is running and configured

### Debugging

- Check container logs: `GET /gateway/logs`
- Monitor container status: `GET /gateway/status`
- View Docker logs: `docker logs ibkr-gateway`

## Security Considerations

- The gateway runs with your IBKR credentials
- Use appropriate firewall rules for production deployments
- Secure API endpoints with authentication if needed
- Regularly update Docker images for security patches

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review the API documentation at `/docs`
- Open an issue on GitHub
