#!/usr/bin/env python3
"""
Main entry point for BetaFly Stabilization System
Starts web server and controller
"""

import argparse
import threading
import logging
from stabilization_controller import OpticalStabilizationController
from config import ConfigManager
from web_server import run_server, set_controller_instance

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='BetaFly Stabilization System')
    parser.add_argument('--web-port', type=int, default=5000,
                       help='Web server port (default: 5000)')
    parser.add_argument('--web-host', type=str, default='0.0.0.0',
                       help='Web server host (default: 0.0.0.0)')
    parser.add_argument('--no-web', action='store_true',
                       help='Run without web server')
    parser.add_argument('--config', type=str, default=None,
                       help='Configuration file path')
    
    args = parser.parse_args()
    
    # Load configuration
    config_manager = ConfigManager(args.config)
    config = config_manager.config
    
    # Create controller
    controller = OpticalStabilizationController(config)
    set_controller_instance(controller)
    
    if not args.no_web:
        # Start web server in background thread
        web_thread = threading.Thread(
            target=run_server,
            args=(args.web_host, args.web_port, False),
            daemon=True
        )
        web_thread.start()
        logger.info(f"Web server started on http://{args.web_host}:{args.web_port}")
    
    try:
        # Run controller in main thread
        controller.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    main()
