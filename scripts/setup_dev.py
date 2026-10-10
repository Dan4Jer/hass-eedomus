#!/usr/bin/env python3
"""Setup script for hass-eedomus development environment."""

import subprocess
import sys
import venv


def create_venv(venv_path=".venv"):
    """Create a virtual environment."""
    print(f"🐍 Creating virtual environment at {venv_path}...")
    venv.create(venv_path, with_pip=True)
    print("✅ Virtual environment created")


def install_requirements(venv_path=".venv"):
    """Install development requirements."""
    pip_path = (
        f"{venv_path}/bin/pip"
        if sys.platform != "win32"
        else f"{venv_path}/Scripts/pip"
    )

    print("📦 Installing development requirements...")
    subprocess.run([pip_path, "install", "--upgrade", "pip"])
    subprocess.run([pip_path, "install", "-r", "requirements.txt"])
    print("✅ Requirements installed")


def main():
    """Main setup function."""
    print("🚀 Setting up hass-eedomus development environment...")

    # Create virtual environment
    create_venv()

    # Install requirements
    install_requirements()

    print("\n🎉 Development environment ready!")
    print("Activate with:")
    if sys.platform == "win32":
        print("  .venv\Scripts\activate")
    else:
        print("  source .venv/bin/activate")


if __name__ == "__main__":
    main()
