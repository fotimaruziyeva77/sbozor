"""agent_gateway — CamAgent'lar bilan gaplashadigan server moduli.

sbozor ichiga shunday ulanadi:

    from agent_gateway.app import build_router
    app.include_router(build_router(data_dir="/var/sbozor/agent_data"))

Mustaqil (dev) rejimda:  python -m agent_gateway
Protokol: docs/protocol.md (v1, muzlatilgan).
"""

__version__ = "0.4.0"
