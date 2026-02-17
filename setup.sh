# Check for pipx
if ! command -v pipx &> /dev/null; then
    echo "pipx not found. Installing..."
    # Try apt first (debian/ubuntu)
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install -y pipx || python3 -m pip install --user --break-system-packages pipx
    else
        python3 -m pip install --user --break-system-packages pipx
    fi
    echo "Ensuring pipx is in PATH..."
    python3 -m pipx ensurepath
    export PATH=$PATH:~/.local/bin
fi

# Install current directory as package
echo "Installing oreilly-dl via pipx..."
pipx install . --force
