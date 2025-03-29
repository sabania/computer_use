#!/bin/bash
set -e

export DISPLAY=:99

# Clean up any old Xvfb or x11vnc processes and lock files
sudo rm -rf /tmp/.X*-lock /tmp/.X11-unix/X*

echo "Starting Xvfb..."
Xvfb :99 -screen 0 1280x800x24 -ac -extension RANDR &
XVFB_PID=$!
sleep 2

echo "Verifying Xvfb is running..."
if ! ps -p $XVFB_PID > /dev/null; then
    echo "ERROR: Xvfb failed to start"
    exit 1
fi

echo "Starting x11vnc..."
# Removed the -noscaling option which was not recognized
x11vnc -display :99 -rfbauth $HOME/.vnc/passwd -listen 0.0.0.0 -rfbport 5900 -noxdamage -forever -bg -shared &
sleep 2

echo "Verifying x11vnc is running..."
if ! pgrep x11vnc > /dev/null; then
    echo "ERROR: x11vnc failed to start"
    exit 1
fi

echo "Starting Xfce4 session..."
dbus-launch --exit-with-session startxfce4 &
XFCE_PID=$!
sleep 3

echo "Starting noVNC..."
/usr/local/share/noVNC/utils/novnc_proxy --vnc localhost:5900 --listen 0.0.0.0:6080 --web /usr/local/share/noVNC/ &
NOVNC_PID=$!
sleep 2

echo "Checking noVNC status..."
if ! ps -p $NOVNC_PID > /dev/null; then
    echo "ERROR: noVNC failed to start"
    exit 1
fi

echo "-----------------------------------------"
echo "Default password is: secret"
echo "-----------------------------------------"
echo "Services started successfully!"
echo "To access the VNC server:"
echo "1. Direct VNC: localhost:5900 (password: secret)"
echo "2. Browser noVNC: http://localhost:6080/vnc.html"

# Keep container running and show logs
tail -f /dev/null