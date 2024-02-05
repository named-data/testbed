FROM ndn_working_base

RUN sudo apt install libpcap-dev & \
    git clone https://github.com/named-data/ndn-tools & \
    cd ndn-tools & \
    ./waf configure & \
    ./waf & \
    sudo ./waf install