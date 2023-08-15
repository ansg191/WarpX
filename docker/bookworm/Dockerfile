FROM debian:bookworm

ARG WARPX_DIM="3"
ARG WARPX_CONFIGURE_OPTIONS="-DWarpX_MPI=ON -DWarpX_EB=OFF -DWarpX_OPENPMD=ON -DWarpX_QED=OFF -DWarpX_PYTHON=ON -DWarpX_PSATD=OFF -DWarpX_COMPUTE=NOACC -DWarpX_PRECISION=DOUBLE"

WORKDIR /warpx

RUN apt-get update && \
    apt-get install -y --no-install-recommends git sudo build-essential ccache cmake g++ git libfftw3-mpi-dev libfftw3-dev libhdf5-openmpi-dev libopenmpi-dev pkg-config python3 python3-dev python3-matplotlib python3-numpy python3-pandas python3-pip python3-scipy python3-venv

COPY . /warpx

RUN GIT_SSL_NO_VERIFY=1 cmake -S . -B build -DWarpX_DIMS=$WARPX_DIM ${WARPX_CONFIGURE_OPTIONS} && \
    cmake --build build -j 4

WORKDIR /app

ENTRYPOINT [ "/warpx/build/bin/warpx" ]
