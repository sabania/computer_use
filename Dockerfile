FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Install essential packages
RUN apt-get update && apt-get install -y \
    xfce4 \
    xfce4-goodies \
    x11vnc \
    xvfb \
    xdotool \
    imagemagick \
    x11-apps \
    sudo \
    software-properties-common \
    python3 \
    python3-pip \
    python3-numpy \
    curl \
    wget \
    git \
    net-tools \
    procps \
    nano \
    dbus-x11 \
    findutils \ 
    && apt-get remove -y light-locker xfce4-screensaver xfce4-power-manager || true \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Add the mozillateam PPA and install Firefox ESR
RUN add-apt-repository ppa:mozillateam/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends firefox-esr \
    && update-alternatives --set x-www-browser /usr/bin/firefox-esr \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -ms /bin/bash myuser \
    && echo "myuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Set up noVNC
RUN apt-get update && apt-get install -y \
    python3-websockify \
    python3-setuptools \
    && mkdir -p /usr/local/share/noVNC \
    && git clone https://github.com/novnc/noVNC.git /usr/local/share/noVNC \
    && cd /usr/local/share/noVNC \
    && git checkout v1.4.0 \
    && ln -s vnc.html index.html \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

# Switch to myuser
USER myuser
WORKDIR /home/myuser

# Create VNC password file directly with x11vnc
RUN mkdir -p /home/myuser/.vnc \
    && echo -n "secret" > /home/myuser/.vnc/passwd_plain \
    && x11vnc -storepasswd $(cat /home/myuser/.vnc/passwd_plain) /home/myuser/.vnc/passwd \
    && rm /home/myuser/.vnc/passwd_plain \
    && chmod 600 /home/myuser/.vnc/passwd

# Copy startup script
COPY --chown=myuser:myuser stream.sh /home/myuser/stream.sh
RUN chmod +x /home/myuser/stream.sh

# Expose ports
EXPOSE 5900 6080

# Run startup script
CMD ["/bin/bash", "/home/myuser/stream.sh"]